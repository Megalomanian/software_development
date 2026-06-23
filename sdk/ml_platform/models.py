"""Models API — model registry, version management, download."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class ModelsAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def ids(self) -> list[dict[str, Any]]:
        """Get all model IDs with names and versions (no pagination)."""
        resp = await self._client.get("/api/models/ids")
        resp.raise_for_status()
        return resp.json()

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        resp = await self._client.get(
            "/api/models/", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def get(self, model_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/api/models/{model_id}")
        resp.raise_for_status()
        return resp.json()

    async def register(self, name: str, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.post(
            "/api/models/register",
            json={"name": name, "experiment_id": experiment_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def promote(self, model_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/api/models/{model_id}/promote")
        resp.raise_for_status()
        return resp.json()

    async def delete(self, model_id: str) -> dict[str, Any]:
        resp = await self._client.delete(f"/api/models/{model_id}")
        resp.raise_for_status()
        return resp.json()

    async def download(self, model_id: str, save_path: str | Path) -> Path:
        """Download a trained model as a pickle file."""
        resp = await self._client.get(f"/api/models/{model_id}/download")
        resp.raise_for_status()
        path = Path(save_path)
        path.write_bytes(resp.read())
        return path
