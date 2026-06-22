from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/{deployment_id}/metrics")
async def get_deployment_metrics(
    deployment_id: str,
    time_range: str = "1h",
    db: AsyncSession = Depends(get_db),
):
    service = MonitoringService(db)
    return await service.get_deployment_metrics(deployment_id, time_range)


@router.get("/{deployment_id}/drift")
async def get_data_drift(deployment_id: str, db: AsyncSession = Depends(get_db)):
    service = MonitoringService(db)
    return await service.get_data_drift(deployment_id)
