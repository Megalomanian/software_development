"""Training queue tests — enqueue, status, background processing."""

from __future__ import annotations

import io
import tempfile

import mlflow
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _use_local_mlflow():
    tmp = tempfile.mkdtemp(prefix="mlflow_test_")
    mlflow.set_tracking_uri(f"sqlite:///{tmp}/mlflow.db")
    yield
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
async def queue_client(db_session):
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from backend.api.data import router as data_router
    from backend.api.experiments import router as experiment_router
    from backend.api.models import router as model_router
    from backend.core.dependencies import get_db
    from backend.services.training_queue import TrainingQueue

    TrainingQueue.reset()

    app = FastAPI(title="Queue Test")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")
    app.include_router(model_router, prefix="/api/models")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    TrainingQueue.reset()


async def _upload_and_create_exp(client: AsyncClient, name: str, target: str = "target") -> str:
    csv = b"f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": (f"{name}.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = resp.json()["id"]
    resp = await client.post("/api/experiments/", json={
        "name": name, "dataset_id": ds_id, "target_column": target, "problem_type": "classification",
    })
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_enqueue_experiment(queue_client: AsyncClient):
    exp_id = await _upload_and_create_exp(queue_client, "queue-exp-1")

    resp = await queue_client.post(f"/api/experiments/{exp_id}/enqueue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == exp_id
    assert data["position"] == 1
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_queue_status(queue_client: AsyncClient):
    exp_id = await _upload_and_create_exp(queue_client, "queue-exp-2")

    await queue_client.post(f"/api/experiments/{exp_id}/enqueue")

    resp = await queue_client.get("/api/experiments/queue/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["jobs"]) >= 1
    job = data["jobs"][0]
    assert job["experiment_name"] == "queue-exp-2"


@pytest.mark.asyncio
async def test_enqueue_not_found(queue_client: AsyncClient):
    resp = await queue_client.post("/api/experiments/00000000-0000-0000-0000-000000000000/enqueue")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_enqueue(queue_client: AsyncClient):
    """Enqueue 3 experiments and check queue order."""
    exp1 = await _upload_and_create_exp(queue_client, "batch-1")
    exp2 = await _upload_and_create_exp(queue_client, "batch-2")
    exp3 = await _upload_and_create_exp(queue_client, "batch-3")

    await queue_client.post(f"/api/experiments/{exp1}/enqueue")
    await queue_client.post(f"/api/experiments/{exp2}/enqueue")
    await queue_client.post(f"/api/experiments/{exp3}/enqueue")

    resp = await queue_client.get("/api/experiments/queue/status")
    data = resp.json()
    assert data["total"] == 3
    names = [j["experiment_name"] for j in data["jobs"]]
    assert names == ["batch-1", "batch-2", "batch-3"]


@pytest.mark.asyncio
async def test_queue_background_processing(queue_client: AsyncClient, db_session):
    """Enqueue and wait for background worker to complete training."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from backend.services.training_queue import TrainingQueue

    # Build a session factory from the test session's engine
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    queue = TrainingQueue()
    queue.configure(session_factory)

    exp_id = await _upload_and_create_exp(queue_client, "queue-process")

    await queue_client.post(f"/api/experiments/{exp_id}/enqueue")

    # Wait for background processing (max 30s)
    for _ in range(30):
        await asyncio.sleep(1)
        resp = await queue_client.get("/api/experiments/queue/status")
        status = resp.json()
        # If no pending and no running, worker is done
        if status["pending"] == 0 and status["running"] is None:
            break

    # Check queue status
    resp = await queue_client.get("/api/experiments/queue/status")
    data = resp.json()
    assert data["pending"] == 0

    # Check experiment status
    resp = await queue_client.get(f"/api/experiments/{exp_id}")
    exp = resp.json()
    assert exp["status"] in ("completed", "running")

    # Check MLflow metrics
    resp = await queue_client.get(f"/api/experiments/{exp_id}/mlflow-metrics")
    metrics = resp.json()
    assert "metrics" in metrics
