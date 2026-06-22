from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.services.training_service import TrainingService

router = APIRouter()


@router.get("/")
async def list_experiments(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = TrainingService(db)
    return await service.list_experiments(offset, limit)


@router.post("/")
async def create_experiment(data: dict, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    return await service.create_experiment(data)


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    experiment = await service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post("/{experiment_id}/run")
async def run_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    return await service.run_experiment(experiment_id)


@router.post("/{experiment_id}/run-sklearn")
async def run_experiment_sklearn(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    return await service.run_experiment_sklearn(experiment_id)


@router.get("/{experiment_id}/mlflow-metrics")
async def get_mlflow_metrics(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    return await service.get_mlflow_metrics(experiment_id)
