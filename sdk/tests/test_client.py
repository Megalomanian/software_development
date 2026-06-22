"""SDK client tests — require the API server to be running."""

from __future__ import annotations

import os

import pytest

from ml_platform import Client

pytestmark = pytest.mark.skipif(
    os.environ.get("CI") != "true",
    reason="Requires running API server (set CI=true or start API manually)",
)


@pytest.mark.asyncio
async def test_health(client: Client):
    result = await client.health()
    assert result["status"] == "ok"
