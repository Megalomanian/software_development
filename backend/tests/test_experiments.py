from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.fixture
async def dataset_id(client: AsyncClient) -> str:
    csv = b"f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("exp_data.csv", io.BytesIO(csv), "text/csv")},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_experiments_empty(client: AsyncClient):
    resp = await client.get("/api/experiments/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_experiment(client: AsyncClient, dataset_id: str):
    resp = await client.post(
        "/api/experiments/",
        json={
            "name": "test-exp",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
            "description": "Test experiment for classification",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-exp"
    assert data["problem_type"] == "classification"
    assert data["status"] == "pending"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_experiments(client: AsyncClient, dataset_id: str):
    await client.post(
        "/api/experiments/",
        json={
            "name": "exp1",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    await client.post(
        "/api/experiments/",
        json={
            "name": "exp2",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "regression",
        },
    )
    resp = await client.get("/api/experiments/")
    assert resp.status_code == 200
    exps = resp.json()
    assert len(exps) == 2


@pytest.mark.asyncio
async def test_get_experiment(client: AsyncClient, dataset_id: str):
    create_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "get-exp",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    exp_id = create_resp.json()["id"]

    resp = await client.get(f"/api/experiments/{exp_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get-exp"


@pytest.mark.asyncio
async def test_get_experiment_not_found(client: AsyncClient):
    resp = await client.get("/api/experiments/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_experiment(client: AsyncClient, dataset_id: str):
    import mlflow

    try:
        mlflow.set_tracking_uri("http://localhost:5000")
        mlflow.get_experiment_by_name("test")
    except Exception:
        pytest.skip("MLflow server not available")

    create_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "run-exp",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    exp_id = create_resp.json()["id"]

    resp = await client.post(f"/api/experiments/{exp_id}/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "mlflow_run_id" in data


@pytest.mark.asyncio
async def test_get_mlflow_metrics(client: AsyncClient, dataset_id: str):
    import mlflow

    try:
        mlflow.set_tracking_uri("http://localhost:5000")
        mlflow.get_experiment_by_name("test")
    except Exception:
        pytest.skip("MLflow server not available")

    create_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "metrics-exp",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    exp_id = create_resp.json()["id"]
    await client.post(f"/api/experiments/{exp_id}/run")

    resp = await client.get(f"/api/experiments/{exp_id}/mlflow-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "params" in data


@pytest.mark.asyncio
async def test_create_experiment_without_name(client: AsyncClient, dataset_id: str):
    resp = await client.post(
        "/api/experiments/",
        json={
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] is not None  # auto-generated


@pytest.mark.asyncio
async def test_create_experiment_with_description(client: AsyncClient, dataset_id: str):
    resp = await client.post(
        "/api/experiments/",
        json={
            "name": "desc-exp",
            "dataset_id": dataset_id,
            "target_column": "target",
            "problem_type": "regression",
            "description": "A regression experiment with random forest",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "desc-exp"
    assert data["description"] == "A regression experiment with random forest"
