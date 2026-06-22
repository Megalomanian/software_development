"""Deployments API — deploy models and run predictions."""

from __future__ import annotations

from typing import Any

import httpx


class DeploymentsAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """List deployments."""
        resp = await self._client.get(
            "/api/deployments/", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def get(self, deployment_id: str) -> dict[str, Any]:
        """Get a deployment by ID."""
        resp = await self._client.get(f"/api/deployments/{deployment_id}")
        resp.raise_for_status()
        return resp.json()

    async def create(
        self, model_version_id: str, replicas: int = 1
    ) -> dict[str, Any]:
        """Deploy a model version to Ray Serve.

        Args:
            model_version_id: ID of the model version to deploy.
            replicas: Number of Ray Serve replicas.
        """
        resp = await self._client.post(
            "/api/deployments/",
            json={"model_version_id": model_version_id, "replicas": replicas},
        )
        resp.raise_for_status()
        return resp.json()

    async def stop(self, deployment_id: str) -> dict[str, Any]:
        """Stop a deployment."""
        resp = await self._client.post(f"/api/deployments/{deployment_id}/stop")
        resp.raise_for_status()
        return resp.json()

    async def predict(self, deployment_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Send a prediction request to a deployed model.

        Args:
            deployment_id: Deployment ID.
            data: Input features as a dict.
        """
        resp = await self._client.post(
            f"/api/deployments/{deployment_id}/predict", json=data
        )
        resp.raise_for_status()
        return resp.json()
