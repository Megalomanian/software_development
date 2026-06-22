"""Manages model deployments on Ray Serve."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import mlflow


class RayServeManager:
    """Handles deploying/stopping models on Ray Serve."""

    def __init__(self, ray_address: str = "auto"):
        self.ray_address = ray_address

    def deploy_model(
        self,
        model_uri: str,
        deployment_name: str,
        num_replicas: int = 1,
    ) -> dict[str, Any]:
        """Deploy a model from MLflow model URI to Ray Serve.

        Returns deployment info including endpoint URL.
        """
        # Generate Ray Serve deployment script
        script = self._generate_deploy_script(model_uri, deployment_name, num_replicas)
        script_path = Path(f"/tmp/ray_deploy_{deployment_name}.py")
        script_path.write_text(script)

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "RAY_ADDRESS": self.ray_address},
            )
            if result.returncode != 0:
                return {"status": "failed", "error": result.stderr.strip()}
            return {"status": "running", "endpoint": f"http://localhost:8000/{deployment_name}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
        finally:
            script_path.unlink(missing_ok=True)

    def stop_deployment(self, deployment_name: str) -> dict[str, Any]:
        script = f"""
import ray
from ray import serve
ray.init(address="{self.ray_address}", ignore_reinit_error=True)
serve.start(detached=True)
serve.delete("{deployment_name}", _blocking=False)
print("OK")
"""
        script_path = Path(f"/tmp/ray_stop_{deployment_name}.py")
        script_path.write_text(script)
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True, timeout=30,
            )
            return {"status": "stopped", "output": result.stdout.strip()}
        finally:
            script_path.unlink(missing_ok=True)

    def predict(self, deployment_name: str, data: dict) -> dict[str, Any]:
        """Send a prediction request to a deployed model."""
        import httpx
        try:
            resp = httpx.post(
                f"http://localhost:8000/{deployment_name}",
                json=data,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _generate_deploy_script(model_uri: str, deployment_name: str, replicas: int) -> str:
        return f'''
import ray
from ray import serve
from ray.serve import PredictorDeployment
import mlflow
import pandas as pd

ray.init(address="auto", ignore_reinit_error=True)
serve.start(detached=True)

class MLModel:
    def __init__(self):
        self.model = mlflow.sklearn.load_model("{model_uri}")

    async def __call__(self, request):
        data = await request.json()
        df = pd.DataFrame([data])
        pred = self.model.predict(df)
        return {{"prediction": pred.tolist()}}

serve.run(
    MLModel.bind(),
    name="{deployment_name}",
    route_prefix="/{deployment_name}",
    num_replicas={replicas},
)
print("DEPLOYED /{deployment_name}")
'''
