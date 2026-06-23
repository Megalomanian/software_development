from __future__ import annotations

import contextlib
import io
import json
import os
import uuid

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models_db.dataset import Dataset, DatasetColumn


class DataService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_datasets(self, offset: int, limit: int) -> list[Dataset]:
        result = await self.db.execute(
            select(Dataset).order_by(Dataset.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def get_dataset(self, dataset_id: str) -> Dataset | None:
        result = await self.db.execute(select(Dataset).where(Dataset.id == dataset_id))
        return result.scalar_one_or_none()

    async def ingest_file(self, file: UploadFile) -> Dataset:
        upload_dir = "/tmp/ml-platform/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        content = await file.read()
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(content)

        df = pd.read_csv(io.BytesIO(content)) if file.filename.endswith(".csv") else pd.DataFrame()

        profile = self._generate_profile(df)

        dataset = Dataset(
            name=file.filename,
            file_path=file_path,
            file_type=file.filename.rsplit(".", 1)[-1] if "." in file.filename else "",
            row_count=len(df),
            column_count=len(df.columns),
            size_bytes=len(content),
            profile=json.dumps(profile),
        )
        self.db.add(dataset)
        await self.db.flush()

        for col_info in profile["columns"]:
            col = DatasetColumn(
                dataset_id=str(dataset.id),
                name=col_info["name"],
                dtype=col_info["dtype"],
                null_count=col_info["null_count"],
                null_ratio=col_info["null_ratio"],
                unique_count=col_info["unique_count"],
                mean=col_info.get("mean"),
                std=col_info.get("std"),
                min_val=col_info.get("min"),
                max_val=col_info.get("max"),
                histogram=json.dumps(col_info.get("histogram", [])),
            )
            self.db.add(col)

        await self.db.commit()
        return dataset

    async def get_profile(self, dataset_id: str) -> dict | None:
        # Return the full profile JSON stored at upload time (includes top_values for strings)
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset or not dataset.profile:
            return None
        try:
            return json.loads(dataset.profile)
        except (json.JSONDecodeError, TypeError):
            return None

    async def preview(self, dataset_id: str, rows: int = 10) -> dict:
        """Return first N rows of a dataset as JSON."""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        try:
            df = pd.read_csv(dataset.file_path)
            preview_rows = df.head(rows).fillna("").to_dict(orient="records")
            return {
                "dataset_id": dataset_id,
                "columns": list(df.columns),
                "rows": preview_rows,
                "total_rows": len(df),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def delete_dataset(self, dataset_id: str) -> dict:
        """Delete a dataset, its columns, and the uploaded file."""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Delete columns
        await self.db.execute(
            delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
        )
        # Delete file
        with contextlib.suppress(OSError):
            os.remove(dataset.file_path)
        # Delete record
        await self.db.delete(dataset)
        await self.db.commit()
        return {"deleted": dataset_id, "name": dataset.name}

    def _generate_profile(self, df: pd.DataFrame) -> dict:
        columns = []
        for col in df.columns:
            series = df[col]
            col_info = {
                "name": col,
                "dtype": str(series.dtype),
                "null_count": int(series.isnull().sum()),
                "null_ratio": float(series.isnull().mean()),
                "unique_count": int(series.nunique()),
            }
            if pd.api.types.is_numeric_dtype(series):
                col_info["mean"] = float(series.mean()) if not series.isnull().all() else None
                col_info["std"] = float(series.std()) if not series.isnull().all() else None
                col_info["min"] = float(series.min()) if not series.isnull().all() else None
                col_info["max"] = float(series.max()) if not series.isnull().all() else None
                hist, bins = pd.cut(series.dropna(), bins=10, retbins=True)
                col_info["histogram"] = [
                    {"bin": f"{bins[i]:.2f}-{bins[i+1]:.2f}", "count": int(count)}
                    for i, count in enumerate(hist.value_counts().sort_index())
                ]
            else:
                value_counts = series.value_counts().head(20)
                col_info["top_values"] = [
                    {"value": str(k), "count": int(v)} for k, v in value_counts.items()
                ]
            columns.append(col_info)

        return {"columns": columns, "total_rows": len(df), "total_columns": len(df.columns)}
