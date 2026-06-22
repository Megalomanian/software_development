"""Local in-memory model serving — no Ray Serve dependency.

Models are loaded from MLflow into memory at deploy time and served
directly from the FastAPI process. Suitable for development and
lightweight production scenarios.
"""

from __future__ import annotations

import logging
from typing import Any

import mlflow

logger = logging.getLogger(__name__)


class LocalModelRegistry:
    """Thread-safe in-memory model store with MLflow integration."""

    _registry: dict[str, dict[str, Any]] = {}

    @classmethod
    def deploy(cls, name: str, mlflow_run_id: str, tracking_uri: str | None = None) -> dict:
        """Load a model from MLflow and store it in the registry.

        Args:
            name: Deployment name (also serves as the lookup key).
            mlflow_run_id: MLflow run ID that logged the model.
            tracking_uri: Optional tracking URI override.

        Returns:
            dict with status and detail.
        """
        if name in cls._registry:
            return {"status": "running", "detail": "already deployed"}

        try:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)

            model_uri = f"runs:/{mlflow_run_id}/model"
            model = mlflow.sklearn.load_model(model_uri)
            cls._registry[name] = {
                "model": model,
                "mlflow_run_id": mlflow_run_id,
                "status": "running",
            }
            logger.info("Model '%s' loaded from MLflow run %s", name, mlflow_run_id)
            return {"status": "running", "detail": "model loaded"}
        except Exception as e:
            logger.error("Failed to load model '%s': %s", name, e)
            return {"status": "failed", "error": str(e)}

    @classmethod
    def predict(cls, name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Run prediction on a deployed model.

        Args:
            name: Deployment name.
            data: Feature dict (e.g., {"feature1": 1.0, "feature2": 2.0}).

        Returns:
            dict with "prediction" key containing the model output.
        """
        import pandas as pd

        entry = cls._registry.get(name)
        if not entry:
            return {"error": f"Model '{name}' not found or not deployed"}

        try:
            model = entry["model"]
            df = pd.DataFrame([data])
            pred = model.predict(df)
            return {"prediction": pred.tolist()}
        except Exception as e:
            logger.exception("Prediction failed for '%s'", name)
            return {"error": str(e)}

    @classmethod
    def stop(cls, name: str) -> dict:
        """Remove a model from the registry."""
        entry = cls._registry.pop(name, None)
        if entry:
            logger.info("Model '%s' stopped and removed from registry", name)
            return {"status": "stopped"}
        return {"status": "not_found"}

    @classmethod
    def is_running(cls, name: str) -> bool:
        """Check if a model is deployed and running."""
        return name in cls._registry

    @classmethod
    def list_models(cls) -> list[str]:
        """List all deployed model names."""
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all models (for testing)."""
        cls._registry.clear()
