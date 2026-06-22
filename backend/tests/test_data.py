from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_datasets_empty(client: AsyncClient):
    resp = await client.get("/api/data/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_upload_csv(client: AsyncClient):
    csv_content = b"name,age,salary\nAlice,30,50000\nBob,25,60000\nCarol,35,75000\n"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test.csv"
    assert data["row_count"] == 3
    assert data["column_count"] == 3
    assert data["file_type"] == "csv"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_datasets_after_upload(client: AsyncClient):
    csv_content = b"x,y\n1,2\n3,4\n"
    await client.post(
        "/api/data/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")},
    )
    resp = await client.get("/api/data/")
    assert resp.status_code == 200
    datasets = resp.json()
    assert len(datasets) == 1
    assert datasets[0]["name"] == "data.csv"


@pytest.mark.asyncio
async def test_get_dataset(client: AsyncClient):
    csv_content = b"a,b,c\n1,2,3\n4,5,6\n7,8,9\n"
    upload_resp = await client.post(
        "/api/data/upload",
        files={"file": ("get.csv", io.BytesIO(csv_content), "text/csv")},
    )
    ds_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/data/{ds_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get.csv"


@pytest.mark.asyncio
async def test_get_dataset_not_found(client: AsyncClient):
    resp = await client.get("/api/data/ffffffff-ffff-ffff-ffff-ffffffffffff")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    csv_content = b"name,age\nAlice,30\nBob,25\nCarol,35\n"
    upload_resp = await client.post(
        "/api/data/upload",
        files={"file": ("profile.csv", io.BytesIO(csv_content), "text/csv")},
    )
    ds_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/data/{ds_id}/profile")
    assert resp.status_code == 200
    profile = resp.json()
    assert "columns" in profile
    columns = {c["name"]: c for c in profile["columns"]}
    assert "name" in columns
    assert "age" in columns
    # age is numeric, should have stats
    assert columns["age"]["mean"] is not None
    assert columns["age"]["min"] is not None
    assert columns["age"]["max"] is not None


@pytest.mark.asyncio
async def test_upload_non_csv(client: AsyncClient):
    """Non-CSV files return empty profile but still create entry."""
    content = b"binary content here"
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("data.bin", io.BytesIO(content), "application/octet-stream")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_type"] == "bin"
    assert data["row_count"] == 0


@pytest.mark.asyncio
async def test_upload_large_csv(client: AsyncClient):
    lines = ["a,b,c,d"] + [f"{i},{i*2},{i*3},{i*4}" for i in range(1000)]
    csv_content = "\n".join(lines).encode()
    resp = await client.post(
        "/api/data/upload",
        files={"file": ("large.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 1000
    assert data["column_count"] == 4
