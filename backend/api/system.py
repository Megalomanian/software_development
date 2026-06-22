"""System-level endpoints — status, stats, health overview."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.models_db.dataset import Dataset
from backend.models_db.experiment import Experiment
from backend.models_db.model import Deployment, ModelVersion

router = APIRouter()


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    """Aggregate counts and running deployments overview."""

    # Count all entities
    datasets = await db.scalar(select(func.count(Dataset.id)))
    experiments = await db.scalar(select(func.count(Experiment.id)))
    models = await db.scalar(select(func.count(ModelVersion.id)))
    deployments = await db.scalar(select(func.count(Deployment.id)))

    # Running deployments
    running = await db.scalar(
        select(func.count(Deployment.id)).where(Deployment.status == "running")
    )

    # Recent experiments (last 5)
    recent_exps = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc()).limit(5)
    )
    recent = [
        {"id": e.id, "name": e.name, "status": e.status, "created_at": str(e.created_at)}
        for e in recent_exps.scalars().all()
    ]

    # Running deployment names
    running_deps = await db.execute(
        select(Deployment).where(Deployment.status == "running")
    )
    running_list = [
        {"id": d.id, "name": d.name, "endpoint_url": d.endpoint_url}
        for d in running_deps.scalars().all()
    ]

    return {
        "server": "ok",
        "counts": {
            "datasets": datasets,
            "experiments": experiments,
            "models": models,
            "deployments": deployments,
            "running_deployments": running,
        },
        "recent_experiments": recent,
        "running_deployments_list": running_list,
    }
