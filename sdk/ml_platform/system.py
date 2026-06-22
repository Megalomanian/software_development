"""System API — server status and health overview."""

from __future__ import annotations

from typing import Any

import httpx


class SystemAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def status(self) -> dict[str, Any]:
        """Get aggregate server status: entity counts, recent experiments, running deployments."""
        resp = await self._client.get("/api/system/status")
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> dict[str, Any]:
        """Simple health check."""
        resp = await self._client.get("/api/health")
        resp.raise_for_status()
        return resp.json()
