"""Main client class for the ML Platform API."""

from __future__ import annotations

from typing import Any

import httpx

from ml_platform.data import DataAPI
from ml_platform.deployments import DeploymentsAPI
from ml_platform.experiments import ExperimentsAPI
from ml_platform.models import ModelsAPI
from ml_platform.monitoring import MonitoringAPI
from ml_platform.system import SystemAPI


class Client:
    """Async client for the ML Platform API.

    Args:
        base_url: Base URL of the ML Platform API (default: http://localhost:8000).

    Example::

        client = Client("http://localhost:8000")
        datasets = await client.data.list()
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)

        self.data = DataAPI(self._client)
        self.experiments = ExperimentsAPI(self._client)
        self.models = ModelsAPI(self._client)
        self.deployments = DeploymentsAPI(self._client)
        self.monitoring = MonitoringAPI(self._client)
        self.system = SystemAPI(self._client)

    async def health(self) -> dict[str, Any]:
        """Check API health."""
        resp = await self._client.get("/api/health")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
