"""Experiments API — create, run, compare, and track ML experiments."""

from __future__ import annotations

from typing import Any

import httpx


class ExperimentsAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def ids(self) -> list[dict[str, Any]]:
        """Get all experiment IDs with names (no pagination)."""
        resp = await self._client.get("/api/experiments/ids")
        resp.raise_for_status()
        return resp.json()

    async def list(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        resp = await self._client.get(
            "/api/experiments/", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    async def get(self, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/api/experiments/{experiment_id}")
        resp.raise_for_status()
        return resp.json()

    async def create(
        self,
        name: str,
        dataset_id: str,
        target_column: str = "target",
        problem_type: str = "classification",
        description: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "dataset_id": dataset_id,
            "target_column": target_column,
            "problem_type": problem_type,
        }
        if description:
            body["description"] = description
        resp = await self._client.post("/api/experiments/", json=body)
        resp.raise_for_status()
        return resp.json()

    async def run(self, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/api/experiments/{experiment_id}/run")
        resp.raise_for_status()
        return resp.json()

    async def run_sklearn(self, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/api/experiments/{experiment_id}/run-sklearn")
        resp.raise_for_status()
        return resp.json()

    async def get_metrics(self, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/api/experiments/{experiment_id}/mlflow-metrics")
        resp.raise_for_status()
        return resp.json()

    async def compare(self, *ids: str) -> list[dict[str, Any]]:
        """Compare metrics across multiple experiments."""
        resp = await self._client.get(
            "/api/experiments/compare", params={"ids": ",".join(ids)}
        )
        resp.raise_for_status()
        return resp.json()

    async def delete(self, experiment_id: str) -> dict[str, Any]:
        resp = await self._client.delete(f"/api/experiments/{experiment_id}")
        resp.raise_for_status()
        return resp.json()
