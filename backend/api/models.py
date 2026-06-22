from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.services.model_service import ModelService

router = APIRouter()


@router.get("/")
async def list_models(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = ModelService(db)
    return await service.list_models(offset, limit)


@router.get("/{model_id}")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/{model_id}/promote")
async def promote_model(model_id: str, db: AsyncSession = Depends(get_db)):
    service = ModelService(db)
    return await service.promote_model(model_id)


@router.post("/register")
async def register_model(data: dict, db: AsyncSession = Depends(get_db)):
    service = ModelService(db)
    return await service.register_from_experiment(data["name"], data["experiment_id"])
