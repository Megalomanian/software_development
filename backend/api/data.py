from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.dependencies import get_db
from backend.models_db.user import User
from backend.services.data_service import DataService

router = APIRouter()


@router.get("/")
async def list_datasets(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = DataService(db)
    return await service.list_datasets(offset, limit)


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    service = DataService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/upload")
async def upload_dataset(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DataService(db)
    return await service.ingest_file(file)


@router.get("/{dataset_id}/profile")
async def get_dataset_profile(dataset_id: str, db: AsyncSession = Depends(get_db)):
    service = DataService(db)
    profile = await service.get_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str, rows: int = Query(10, ge=1, le=100), db: AsyncSession = Depends(get_db)
):
    """Preview first N rows of a dataset (max 100)."""
    service = DataService(db)
    return await service.preview(dataset_id, rows)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DataService(db)
    return await service.delete_dataset(dataset_id)
