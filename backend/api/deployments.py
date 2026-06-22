from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.dependencies import get_db
from backend.models_db.model import Deployment
from backend.models_db.user import User
from backend.services.deployment_service import DeploymentService

router = APIRouter()


@router.get("/")
async def list_deployments(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = DeploymentService(db)
    return await service.list_deployments(offset, limit)


@router.post("/")
async def create_deployment(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeploymentService(db)
    return await service.create_deployment(data)


@router.get("/{deployment_id}")
async def get_deployment(deployment_id: str, db: AsyncSession = Depends(get_db)):
    service = DeploymentService(db)
    deployment = await service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeploymentService(db)
    return await service.stop_deployment(deployment_id)


@router.post("/{deployment_id}/predict")
async def predict(deployment_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    service = DeploymentService(db)
    return await service.predict(deployment_id, data)


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deployment = await db.scalar(
        select(Deployment).where(Deployment.id == deployment_id)
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Stop the model if running
    try:
        from backend.services.deployment_service import DeploymentService
        svc = DeploymentService(db)
        await svc.stop_deployment(deployment_id)
    except Exception:
        pass

    await db.delete(deployment)
    await db.commit()
    return {"deleted": deployment_id, "name": deployment.name}
