from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.fixture
async def experiment_id(client: AsyncClient) -> str:
    csv = b"f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n"
    upload_resp = await client.post(
        "/api/data/upload",
        files={"file": ("model_data.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = upload_resp.json()["id"]

    create_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "model-exp",
            "dataset_id": ds_id,
            "target_column": "target",
            "problem_type": "classification",
            "nodes": [],
            "edges": [],
        },
    )
    return create_resp.json()["id"]


@pytest.mark.asyncio
async def test_list_models_empty(client: AsyncClient):
    resp = await client.get("/api/models/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_register_model(client: AsyncClient, experiment_id: str):
    resp = await client.post(
        "/api/models/register",
        json={
            "name": "my-model",
            "experiment_id": experiment_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "my-model"
    assert data["version"] == 1
    assert data["status"] == "registered"
    assert data["experiment_id"] == experiment_id


@pytest.mark.asyncio
async def test_list_models_after_register(client: AsyncClient, experiment_id: str):
    await client.post(
        "/api/models/register",
        json={"name": "model-a", "experiment_id": experiment_id},
    )
    await client.post(
        "/api/models/register",
        json={"name": "model-b", "experiment_id": experiment_id},
    )

    resp = await client.get("/api/models/")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) == 2


@pytest.mark.asyncio
async def test_promote_model(client: AsyncClient, experiment_id: str):
    create_resp = await client.post(
        "/api/models/register",
        json={"name": "promotable", "experiment_id": experiment_id},
    )
    model_id = create_resp.json()["id"]

    resp = await client.post(f"/api/models/{model_id}/promote")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "promotable"
    assert data["version"] == 2  # promoted from v1


@pytest.mark.asyncio
async def test_get_model(client: AsyncClient, experiment_id: str):
    create_resp = await client.post(
        "/api/models/register",
        json={"name": "gettable", "experiment_id": experiment_id},
    )
    model_id = create_resp.json()["id"]

    resp = await client.get(f"/api/models/{model_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "gettable"


@pytest.mark.asyncio
async def test_register_with_nonexistent_experiment(client: AsyncClient):
    resp = await client.post(
        "/api/models/register",
        json={
            "name": "bad-model",
            "experiment_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        },
    )
    assert resp.status_code == 404
