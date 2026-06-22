from __future__ import annotations

import json
import uuid
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.models_db.dataset import Dataset, DatasetColumn
from backend.services.data_service import DataService

router = APIRouter()


@router.get("/")
async def list_datasets(
    offset: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    service = DataService(db)
    datasets = await service.list_datasets(offset, limit)
    return datasets


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    service = DataService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/upload")
async def upload_dataset(file: UploadFile, db: AsyncSession = Depends(get_db)):
    service = DataService(db)
    dataset = await service.ingest_file(file)
    return dataset


@router.get("/{dataset_id}/profile")
async def get_dataset_profile(dataset_id: str, db: AsyncSession = Depends(get_db)):
    service = DataService(db)
    profile = await service.get_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
