from __future__ import annotations

import uuid
from typing import Any

import mlflow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models_db.dataset import Dataset
from backend.models_db.experiment import Experiment

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)


class TrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_experiments(self, offset: int, limit: int) -> list[Experiment]:
        result = await self.db.execute(
            select(Experiment)
            .order_by(Experiment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_experiment(self, data: dict) -> Experiment:
        experiment = Experiment(
            name=data.get("name", f"Experiment_{uuid.uuid4().hex[:8]}"),
            dataset_id=data.get("dataset_id"),
            target_column=data.get("target_column", "target"),
            problem_type=data.get("problem_type", "classification"),
            description=data.get("description"),
        )
        self.db.add(experiment)
        await self.db.commit()
        return experiment

    async def get_experiment(self, experiment_id: str) -> Experiment | None:
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        return result.scalar_one_or_none()

    async def run_experiment(self, experiment_id: str) -> dict:
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        mlflow.set_experiment(experiment.name)
        with mlflow.start_run() as run:
            mlflow.log_param("problem_type", experiment.problem_type)
            mlflow.log_param("target_column", experiment.target_column)
            mlflow.log_metric("accuracy", 0.0)

            experiment.mlflow_run_id = run.info.run_id
            experiment.status = "completed"
            await self.db.commit()

        return {
            "experiment_id": experiment_id,
            "mlflow_run_id": run.info.run_id,
            "status": "completed",
        }

    async def run_experiment_sklearn(self, experiment_id: str) -> dict:
        """Execute a pipeline against real data with sklearn, then log to MLflow."""
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
        from sklearn.preprocessing import LabelEncoder

        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Load dataset
        dataset_result = await self.db.execute(
            select(Dataset).where(Dataset.id == experiment.dataset_id)
        )
        ds = dataset_result.scalar_one_or_none()
        if not ds:
            raise ValueError("Dataset not found")

        df = pd.read_csv(ds.file_path)
        y = df[experiment.target_column]
        X = df.drop(columns=[experiment.target_column])

        # Encode categorical columns
        for col in X.select_dtypes(include=["object"]).columns:
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))

        # Train/test split
        split = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # Choose model
        is_cls = experiment.problem_type == "classification"
        if is_cls:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        mlflow.set_experiment(experiment.name)
        with mlflow.start_run() as run:
            mlflow.log_param("problem_type", experiment.problem_type)
            mlflow.log_param("target_column", experiment.target_column)
            mlflow.log_param("rows", len(df))

            if is_cls:
                acc = accuracy_score(y_test, y_pred)
                mlflow.log_metric("accuracy", acc)
            else:
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                mlflow.log_metric("mse", mse)
                mlflow.log_metric("r2", r2)

            mlflow.sklearn.log_model(model, "model")
            experiment.mlflow_run_id = run.info.run_id
            experiment.status = "completed"
            await self.db.commit()

        return {
            "experiment_id": experiment_id,
            "mlflow_run_id": run.info.run_id,
            "status": "completed",
        }

    async def get_mlflow_metrics(self, experiment_id: str) -> dict[str, Any]:
        experiment = await self.get_experiment(experiment_id)
        if not experiment or not experiment.mlflow_run_id:
            return {"metrics": [], "params": []}

        client = mlflow.tracking.MlflowClient()
        run = client.get_run(experiment.mlflow_run_id)
        return {
            "metrics": [{"key": k, "value": v} for k, v in run.data.metrics.items()],
            "params": [{"key": k, "value": v} for k, v in run.data.params.items()],
        }
