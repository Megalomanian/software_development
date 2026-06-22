"""Models API — model registry and version management."""

from __future__ import annotations

from typing import Any

import httpx


class ModelsAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """List registered models."""
        resp = await self._client.get(
            "/api/models/", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def get(self, model_id: str) -> dict[str, Any]:
        """Get a model version by ID."""
        resp = await self._client.get(f"/api/models/{model_id}")
        resp.raise_for_status()
        return resp.json()

    async def register(self, name: str, experiment_id: str) -> dict[str, Any]:
        """Register a model from a completed experiment.

        Args:
            name: Model name.
            experiment_id: ID of the completed experiment.
        """
        resp = await self._client.post(
            "/api/models/register",
            json={"name": name, "experiment_id": experiment_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def promote(self, model_id: str) -> dict[str, Any]:
        """Promote a model to a new version."""
        resp = await self._client.post(f"/api/models/{model_id}/promote")
        resp.raise_for_status()
        return resp.json()
