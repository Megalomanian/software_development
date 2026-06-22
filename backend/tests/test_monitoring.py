from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.fixture
async def deployment_id(client: AsyncClient) -> str:
    csv = b"x,y,t\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n"
    upload_resp = await client.post(
        "/api/data/upload",
        files={"file": ("mon_data.csv", io.BytesIO(csv), "text/csv")},
    )
    ds_id = upload_resp.json()["id"]

    exp_resp = await client.post(
        "/api/experiments/",
        json={
            "name": "mon-exp",
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
        json={"name": "mon-model", "experiment_id": exp_id},
    )
    model_id = model_resp.json()["id"]

    dep_resp = await client.post(
        "/api/deployments/",
        json={"model_version_id": model_id, "replicas": 1},
    )
    return dep_resp.json()["id"]


@pytest.mark.asyncio
async def test_get_deployment_metrics(client: AsyncClient, deployment_id: str):
    resp = await client.get(f"/api/monitoring/{deployment_id}/metrics?time_range=1h")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deployment_id"] == deployment_id
    assert data["time_range"] == "1h"
    assert "metrics" in data
    m = data["metrics"]
    assert "request_count" in m
    assert "avg_latency_ms" in m
    assert "p95_latency_ms" in m
    assert "error_rate" in m
    assert "throughput_rps" in m


@pytest.mark.asyncio
async def test_get_deployment_metrics_different_ranges(client: AsyncClient, deployment_id: str):
    for time_range in ["5m", "15m", "1h", "24h"]:
        resp = await client.get(
            f"/api/monitoring/{deployment_id}/metrics?time_range={time_range}"
        )
        assert resp.status_code == 200
        assert resp.json()["time_range"] == time_range


@pytest.mark.asyncio
async def test_get_data_drift(client: AsyncClient, deployment_id: str):
    resp = await client.get(f"/api/monitoring/{deployment_id}/drift")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deployment_id"] == deployment_id
    assert "drift_detected" in data
    assert "drift_score" in data
    assert "feature_drifts" in data


@pytest.mark.asyncio
async def test_get_data_drift_insufficient_data(client: AsyncClient, deployment_id: str):
    resp = await client.get(f"/api/monitoring/{deployment_id}/drift")
    data = resp.json()
    # Without inference logs, should report insufficient data or no drift
    if "message" in data:
        assert "Not enough" in data["message"] or not data["drift_detected"]


@pytest.mark.asyncio
async def test_monitoring_with_nonexistent_deployment(client: AsyncClient):
    resp = await client.get(
        "/api/monitoring/ffffffff-ffff-ffff-ffff-ffffffffffff/metrics"
    )
    assert resp.status_code == 200  # returns empty metrics, not 404
    assert resp.json()["metrics"]["request_count"] == 0
