"""End-to-end training test with small sample data.

Tests the full pipeline: data upload → experiment creation →
sklearn training → result verification — all with real computation.
Uses local MLflow file store so no server is needed.
"""

from __future__ import annotations

import io
import tempfile

import mlflow
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _use_local_mlflow():
    """Use a local SQLite DB for MLflow instead of requiring a server."""
    tmp = tempfile.mkdtemp(prefix="mlflow_test_")
    mlflow.set_tracking_uri(f"sqlite:///{tmp}/mlflow.db")
    yield
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
async def client(db_session):
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from backend.api.auth import router as auth_router
    from backend.api.data import router as data_router
    from backend.api.deployments import router as deployment_router
    from backend.api.experiments import router as experiment_router
    from backend.api.models import router as model_router
    from backend.api.monitoring import router as monitoring_router
    from backend.core.auth import create_access_token, hash_password
    from backend.core.dependencies import get_db
    from backend.models_db.user import User

    # Create test user for auth
    user = User(
        username="e2e_test", email="e2e@test.com",
        hashed_password=hash_password("test"),
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token({"sub": str(user.id)})

    app = FastAPI(title="E2E Test")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")
    app.include_router(model_router, prefix="/api/models")
    app.include_router(deployment_router, prefix="/api/deployments")
    app.include_router(monitoring_router, prefix="/api/monitoring")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_e2e_classification_training(client):
    """End-to-end: upload CSV → create experiment → run sklearn → verify results."""
    csv_data = (
        b"f1,f2,f3,f4,target\n"
        b"5.1,3.5,1.4,0.2,0\n"
        b"4.9,3.0,1.4,0.2,0\n"
        b"4.7,3.2,1.3,0.2,0\n"
        b"7.0,3.2,4.7,1.4,1\n"
        b"6.4,3.2,4.5,1.5,1\n"
        b"6.9,3.1,4.9,1.5,1\n"
        b"6.3,3.3,6.0,2.5,2\n"
        b"5.8,2.7,5.1,1.9,2\n"
        b"7.1,3.0,5.9,2.1,2\n"
    )
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("iris_small.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert resp.status_code == 200
    dataset = resp.json()
    assert dataset["row_count"] == 9
    assert dataset["column_count"] == 5

    resp = await client.post(
        "/api/experiments/",
        json={
            "name": "e2e-iris-classifier",
            "dataset_id": dataset["id"],
            "target_column": "target",
            "problem_type": "classification",
            "description": "E2E test: iris classification with RandomForest",
        },
    )
    assert resp.status_code == 200
    experiment = resp.json()

    resp = await client.post(f"/api/experiments/{experiment['id']}/run-sklearn")
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "completed"
    assert "mlflow_run_id" in result

    resp = await client.get(f"/api/experiments/{experiment['id']}/mlflow-metrics")
    assert resp.status_code == 200
    mlflow_data = resp.json()
    metrics = {m["key"]: m["value"] for m in mlflow_data["metrics"]}
    assert "accuracy" in metrics
    assert 0.0 <= metrics["accuracy"] <= 1.0

    print(f"\n✅ E2E classification: accuracy={metrics['accuracy']:.3f}")


@pytest.mark.asyncio
async def test_e2e_regression_training(client):
    """End-to-end: regression training with small numeric dataset."""
    csv_data = (
        b"x1,x2,x3,target\n"
        b"1,2,3,10\n"
        b"2,3,4,15\n"
        b"3,4,5,20\n"
        b"4,5,6,25\n"
        b"5,6,7,30\n"
        b"6,7,8,35\n"
        b"7,8,9,40\n"
    )
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("regression.csv", io.BytesIO(csv_data), "text/csv")},
    )
    dataset = resp.json()

    resp = await client.post(
        "/api/experiments/",
        json={
            "name": "e2e-regression",
            "dataset_id": dataset["id"],
            "target_column": "target",
            "problem_type": "regression",
        },
    )
    experiment = resp.json()

    resp = await client.post(f"/api/experiments/{experiment['id']}/run-sklearn")
    result = resp.json()
    assert result["status"] == "completed"

    resp = await client.get(f"/api/experiments/{experiment['id']}/mlflow-metrics")
    mlflow_data = resp.json()
    metrics = {m["key"]: m["value"] for m in mlflow_data["metrics"]}
    assert "r2" in metrics
    print(f"\n✅ E2E regression: R²={metrics['r2']:.3f}")


@pytest.mark.asyncio
async def test_e2e_model_registration(client):
    """End-to-end: train → register model → deploy → verify deployment."""
    csv_data = b"f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("binary.csv", io.BytesIO(csv_data), "text/csv")},
    )
    dataset_id = resp.json()["id"]

    resp = await client.post(
        "/api/experiments/",
        json={
            "name": "e2e-model-reg",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    experiment_id = resp.json()["id"]
    await client.post(f"/api/experiments/{experiment_id}/run-sklearn")

    # Register model from experiment
    resp = await client.post(
        "/api/models/register",
        json={"name": "e2e-model", "experiment_id": experiment_id},
    )
    assert resp.status_code == 200
    model = resp.json()
    assert model["name"] == "e2e-model"
    assert model["status"] == "registered"

    # Promote to new version
    resp = await client.post(f"/api/models/{model['id']}/promote")
    assert resp.status_code == 200
    v2 = resp.json()
    assert v2["version"] == 2

    print(f"\n✅ E2E model registration: v{model['version']} → v{v2['version']}")
