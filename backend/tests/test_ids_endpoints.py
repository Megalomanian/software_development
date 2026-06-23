"""Test the /ids endpoints for experiments and models."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_experiment_ids_empty(client: AsyncClient):
    """GET /api/experiments/ids returns empty list when no experiments exist."""
    resp = await client.get("/api/experiments/ids")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_model_ids_empty(client: AsyncClient):
    """GET /api/models/ids returns empty list when no models exist."""
    resp = await client.get("/api/models/ids")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_experiment_ids_with_data(client: AsyncClient, db_session):
    """GET /api/experiments/ids returns all experiments."""
    # Upload dataset
    csv = b"a,b,target\n1,2,0\n3,4,1\n5,6,0\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("ids-test.csv", io.BytesIO(csv), "text/csv")},
    )
    assert resp.status_code == 200
    ds_id = resp.json()["id"]

    # Create experiments
    resp = await client.post("/api/experiments/", json={
        "name": "ids-exp-1", "dataset_id": ds_id,
        "target_column": "target", "problem_type": "classification",
    })
    assert resp.status_code == 200
    exp1_id = resp.json()["id"]

    resp = await client.post("/api/experiments/", json={
        "name": "ids-exp-2", "dataset_id": ds_id,
        "target_column": "target", "problem_type": "regression",
    })
    assert resp.status_code == 200
    exp2_id = resp.json()["id"]

    # Get ids
    resp = await client.get("/api/experiments/ids")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Verify structure
    ids = {r["id"] for r in data}
    assert exp1_id in ids
    assert exp2_id in ids

    for r in data:
        assert "id" in r
        assert "name" in r
        assert "status" in r


@pytest.mark.asyncio
async def test_model_ids_with_data(client: AsyncClient, db_session):
    """GET /api/models/ids returns all models."""
    # Setup: upload + create experiment
    csv = b"a,b,target\n1,2,0\n3,4,1\n5,6,0\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("ids-test2.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post("/api/experiments/", json={
        "name": "ids-exp", "dataset_id": ds_id,
        "target_column": "target", "problem_type": "classification",
    })
    exp_id = resp.json()["id"]

    # Register models
    resp = await client.post("/api/models/register", json={
        "name": "ids-model-a", "experiment_id": exp_id,
    })
    assert resp.status_code == 200
    m1_id = resp.json()["id"]

    resp = await client.post("/api/models/register", json={
        "name": "ids-model-b", "experiment_id": exp_id,
    })
    assert resp.status_code == 200
    m2_id = resp.json()["id"]

    # Get all ids
    resp = await client.get("/api/models/ids")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    ids = {r["id"] for r in data}
    assert m1_id in ids
    assert m2_id in ids

    for r in data:
        assert "id" in r
        assert "name" in r
        assert "version" in r
        assert "status" in r


@pytest.mark.asyncio
async def test_model_get_still_works_after_ids_route(client: AsyncClient, db_session):
    """Verify GET /api/models/{id} is not broken by the /ids route."""
    csv = b"a,b,target\n1,2,0\n3,4,1\n5,6,0\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("route-test.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post("/api/experiments/", json={
        "name": "route-exp", "dataset_id": ds_id,
        "target_column": "target", "problem_type": "classification",
    })
    exp_id = resp.json()["id"]

    resp = await client.post("/api/models/register", json={
        "name": "route-model", "experiment_id": exp_id,
    })
    model_id = resp.json()["id"]

    # GET /api/models/ids works
    resp = await client.get("/api/models/ids")
    assert resp.status_code == 200

    # GET /api/models/{model_id} still works (not shadowed by /ids)
    resp = await client.get(f"/api/models/{model_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == model_id
    assert resp.json()["name"] == "route-model"


@pytest.mark.asyncio
async def test_experiment_get_still_works(client: AsyncClient, db_session):
    """Verify GET /api/experiments/{id} is not broken by the /ids route."""
    csv = b"a,b,target\n1,2,0\n3,4,1\n5,6,0\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("route-exp.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post("/api/experiments/", json={
        "name": "route-exp-2", "dataset_id": ds_id,
        "target_column": "target", "problem_type": "classification",
    })
    exp_id = resp.json()["id"]

    # GET /api/experiments/ids works
    resp = await client.get("/api/experiments/ids")
    assert resp.status_code == 200

    # GET /api/experiments/{id} still works
    resp = await client.get(f"/api/experiments/{exp_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == exp_id
    assert resp.json()["name"] == "route-exp-2"
