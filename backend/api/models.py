from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db
from backend.models_db.model import ModelVersion
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


@router.delete("/{model_id}")
async def delete_model(model_id: str, db: AsyncSession = Depends(get_db)):
    model = await db.scalar(
        select(ModelVersion).where(ModelVersion.id == model_id)
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    await db.delete(model)
    await db.commit()
    return {"deleted": model_id, "name": model.name, "version": model.version}


@router.get("/{model_id}/download")
async def download_model(model_id: str, db: AsyncSession = Depends(get_db)):
    """Download a trained model artifact as a pickle file."""
    model = await db.scalar(
        select(ModelVersion).where(ModelVersion.id == model_id)
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not model.mlflow_model_uri:
        raise HTTPException(status_code=404, detail="No MLflow artifact for this model")

    import mlflow

    from backend.core.config import settings

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    try:
        model_uri = f"runs:/{model.mlflow_model_uri}/model"
        sklearn_model = mlflow.sklearn.load_model(model_uri)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}") from e

    import io as _io
    import pickle

    from fastapi.responses import StreamingResponse

    buf = _io.BytesIO()
    try:
        pickle.dump(sklearn_model, buf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serialize model: {e}") from e

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{model.name}_v{model.version}.pkl"'
        },
    )
