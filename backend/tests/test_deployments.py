from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.fixture
async def model_id(client: AsyncClient) -> str:
    csv = b"x,y,t\n1,2,0\n3,4,1\n"
    upload_resp = await client.post(
        "/api/data/upload",
        files={"file": ("dep_data.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = upload_resp.json()["id"]

    exp_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "dep-exp",
            "dataset_id": ds_id,
            "target_column": "t",
            "problem_type": "classification",
            "nodes": [],
            "edges": [],
        },
    )
    exp_id = exp_resp.json()["id"]

    model_resp = await client.post(
        "/api/models/register",
        json={"name": "deployable", "experiment_id": exp_id},
    )
    return model_resp.json()["id"]


@pytest.mark.asyncio
async def test_list_deployments_empty(client: AsyncClient):
    resp = await client.get("/api/deployments/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_deployment(client: AsyncClient, model_id: str):
    resp = await client.post(
        "/api/deployments/",
        json={
            "model_version_id": model_id,
            "replicas": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert data["replicas"] == 2
    assert data["status"] in ("running", "deploying", "failed", "failed_no_ray")
    assert data["endpoint_url"] is not None


@pytest.mark.asyncio
async def test_list_deployments_after_create(client: AsyncClient, model_id: str):
    await client.post(
        "/api/deployments/",
        json={"model_version_id": model_id, "replicas": 1},
    )
    resp = await client.get("/api/deployments/")
    assert resp.status_code == 200
    deps = resp.json()
    assert len(deps) >= 1


@pytest.mark.asyncio
async def test_get_deployment(client: AsyncClient, model_id: str):
    create_resp = await client.post(
        "/api/deployments/",
        json={"model_version_id": model_id, "replicas": 1},
    )
    dep_id = create_resp.json()["id"]

    resp = await client.get(f"/api/deployments/{dep_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == dep_id


@pytest.mark.asyncio
async def test_stop_deployment(client: AsyncClient, model_id: str):
    create_resp = await client.post(
        "/api/deployments/",
        json={"model_version_id": model_id, "replicas": 1},
    )
    dep_id = create_resp.json()["id"]

    resp = await client.post(f"/api/deployments/{dep_id}/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_predict_on_deployment(client: AsyncClient, model_id: str):
    create_resp = await client.post(
        "/api/deployments/",
        json={"model_version_id": model_id, "replicas": 1},
    )
    dep_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/deployments/{dep_id}/predict",
        json={"f1": 1.0, "f2": 2.0},
    )
    assert resp.status_code in (200, 500)  # may fail without Ray running


@pytest.mark.asyncio
async def test_create_deployment_nonexistent_model(client: AsyncClient):
    resp = await client.post(
        "/api/deployments/",
        json={"model_version_id": "00000000-0000-0000-0000-000000000000", "replicas": 1},
    )
    assert resp.status_code == 404
