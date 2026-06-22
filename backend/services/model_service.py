from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models_db.experiment import Experiment
from backend.models_db.model import ModelVersion


class ModelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_models(self, offset: int, limit: int) -> list[ModelVersion]:
        result = await self.db.execute(
            select(ModelVersion)
            .order_by(ModelVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_model(self, model_id: str) -> ModelVersion | None:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.id == model_id)
        )
        return result.scalar_one_or_none()

    async def promote_model(self, model_id: str) -> ModelVersion:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        new_version = ModelVersion(
            name=model.name,
            version=model.version + 1,
            experiment_id=model.experiment_id,
            mlflow_model_uri=model.mlflow_model_uri,
            framework=model.framework,
            artifact_path=model.artifact_path,
            status="registered",
        )
        self.db.add(new_version)
        await self.db.commit()
        return new_version

    async def register_from_experiment(self, name: str, experiment_id: str) -> ModelVersion:
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if not experiment:
            raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")

        model = ModelVersion(
            name=name,
            version=1,
            experiment_id=experiment_id,
            mlflow_model_uri=experiment.mlflow_run_id,
            framework="sklearn",
            status="registered",
        )
        self.db.add(model)
        await self.db.commit()
        return model
