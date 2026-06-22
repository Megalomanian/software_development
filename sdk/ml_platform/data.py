"""Data API — upload datasets and inspect profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class DataAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """List uploaded datasets."""
        resp = await self._client.get("/api/data/", params={"offset": offset, "limit": limit})
        resp.raise_for_status()
        return resp.json()

    async def get(self, dataset_id: str) -> dict[str, Any]:
        """Get a dataset by ID."""
        resp = await self._client.get(f"/api/data/{dataset_id}")
        resp.raise_for_status()
        return resp.json()

    async def upload(self, file_path: str | Path) -> dict[str, Any]:
        """Upload a CSV file and return the dataset metadata with profile."""
        path = Path(file_path)
        with open(path, "rb") as f:
            resp = await self._client.post(
                "/api/data/upload",
                files={"file": (path.name, f, "text/csv")},
            )
        resp.raise_for_status()
        return resp.json()

    async def profile(self, dataset_id: str) -> dict[str, Any]:
        """Get the auto-generated profile (column stats, histograms) for a dataset."""
        resp = await self._client.get(f"/api/data/{dataset_id}/profile")
        resp.raise_for_status()
        return resp.json()
