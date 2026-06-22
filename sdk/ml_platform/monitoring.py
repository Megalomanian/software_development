"""Monitoring API — metrics aggregation and drift detection."""

from __future__ import annotations

from typing import Any

import httpx


class MonitoringAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_metrics(
        self, deployment_id: str, time_range: str = "1h"
    ) -> dict[str, Any]:
        """Get deployment metrics (request count, latency, error rate, throughput).

        Args:
            deployment_id: Deployment ID.
            time_range: Time window — ``"5m"``, ``"15m"``, ``"1h"``, ``"6h"``, ``"24h"``, ``"7d"``.
        """
        resp = await self._client.get(
            f"/api/monitoring/{deployment_id}/metrics",
            params={"time_range": time_range},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_drift(self, deployment_id: str) -> dict[str, Any]:
        """Check for data drift on a deployment.

        Uses z-score based drift detection on numeric features (threshold: 2.0).
        Requires 50+ inference samples.
        """
        resp = await self._client.get(f"/api/monitoring/{deployment_id}/drift")
        resp.raise_for_status()
        return resp.json()
