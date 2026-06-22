"""Deployments API — deploy models and run predictions."""

from __future__ import annotations

from typing import Any

import httpx


class DeploymentsAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        resp = await self._client.get(
            "/api/deployments/", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def get(self, deployment_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/api/deployments/{deployment_id}")
        resp.raise_for_status()
        return resp.json()

    async def create(self, model_version_id: str, replicas: int = 1) -> dict[str, Any]:
        resp = await self._client.post(
            "/api/deployments/",
            json={"model_version_id": model_version_id, "replicas": replicas},
        )
        resp.raise_for_status()
        return resp.json()

    async def stop(self, deployment_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/api/deployments/{deployment_id}/stop")
        resp.raise_for_status()
        return resp.json()

    async def predict(self, deployment_id: str, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"/api/deployments/{deployment_id}/predict", json=data
        )
        resp.raise_for_status()
        return resp.json()

    async def delete(self, deployment_id: str) -> dict[str, Any]:
        resp = await self._client.delete(f"/api/deployments/{deployment_id}")
        resp.raise_for_status()
        return resp.json()
