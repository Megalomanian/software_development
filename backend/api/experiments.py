from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.dependencies import get_db
from backend.models_db.experiment import Experiment
from backend.models_db.user import User
from backend.services.training_queue import get_queue
from backend.services.training_service import TrainingService

router = APIRouter()


@router.get("/")
async def list_experiments(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = TrainingService(db)
    return await service.list_experiments(offset, limit)


@router.post("/")
async def create_experiment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
async def run_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = TrainingService(db)
    return await service.run_experiment(experiment_id)


@router.post("/{experiment_id}/run-sklearn")
async def run_experiment_sklearn(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue experiment for sklearn training via FIFO queue.

    Returns immediately with queue position. Training runs asynchronously.
    Monitor progress with GET /api/experiments/queue/status.
    """
    service = TrainingService(db)
    experiment = await service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    queue = get_queue()
    result = await queue.enqueue(
        experiment_id, experiment.name,
        username=current_user.username,
    )
    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment.name,
        "status": "queued",
        "position": result["position"],
        "message": (
            f"Experiment '{experiment.name}' is #{result['position']} in queue. "
            "Check /api/experiments/queue/status for progress."
        ),
    }


@router.get("/{experiment_id}/mlflow-metrics")
async def get_mlflow_metrics(experiment_id: str, db: AsyncSession = Depends(get_db)):
    service = TrainingService(db)
    return await service.get_mlflow_metrics(experiment_id)


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    experiment = await db.scalar(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    await db.delete(experiment)
    await db.commit()
    return {"deleted": experiment_id, "name": experiment.name}


@router.get("/compare")
async def compare_experiments(
    ids: str, db: AsyncSession = Depends(get_db)
):
    """Compare metrics across multiple experiments.

    Query: GET /api/experiments/compare?ids=uuid1,uuid2,uuid3
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No experiment IDs provided")

    result = await db.execute(
        select(Experiment).where(Experiment.id.in_(id_list))
    )
    experiments = result.scalars().all()

    return [
        {
            "id": e.id,
            "name": e.name,
            "target_column": e.target_column,
            "problem_type": e.problem_type,
            "status": e.status,
            "mlflow_run_id": e.mlflow_run_id,
            "metrics": e.metrics,
            "created_at": str(e.created_at),
        }
        for e in experiments
    ]


@router.post("/{experiment_id}/enqueue")
async def enqueue_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an experiment to the training queue."""
    service = TrainingService(db)
    experiment = await service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    queue = get_queue()
    return await queue.enqueue(
        experiment_id, experiment.name,
        username=current_user.username,
    )


@router.get("/queue/status")
async def queue_status():
    """Get the training queue status."""
    return get_queue().get_status()

