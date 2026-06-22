from __future__ import annotations

import os

import pytest

from ml_platform import Client


@pytest.fixture
def base_url() -> str:
    return os.environ.get("MLP_API_URL", "http://localhost:8000")


@pytest.fixture
async def client(base_url: str) -> Client:
    c = Client(base_url)
    yield c
    await c.close()
