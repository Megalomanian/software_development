from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.api.data import router as data_router
from backend.api.deployments import router as deployment_router
from backend.api.experiments import router as experiment_router
from backend.api.models import router as model_router
from backend.api.monitoring import router as monitoring_router
from backend.api.system import router as system_router
from backend.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(data_router, prefix="/api/data", tags=["data"])
app.include_router(experiment_router, prefix="/api/experiments", tags=["experiments"])
app.include_router(model_router, prefix="/api/models", tags=["models"])
app.include_router(deployment_router, prefix="/api/deployments", tags=["deployments"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(system_router, prefix="/api/system", tags=["system"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
