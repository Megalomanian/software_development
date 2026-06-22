"""Data API integration tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from ml_platform import Client

pytestmark = pytest.mark.skipif(
    os.environ.get("CI") != "true",
    reason="Requires running API server (set CI=true or start API manually)",
)


@pytest.mark.asyncio
async def test_upload_and_list(client: Client):
    # Create a small CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n")
        csv_path = f.name

    try:
        dataset = await client.data.upload(csv_path)
        assert dataset["id"] is not None
        assert dataset["name"].endswith(".csv")
        assert dataset["row_count"] == 3
        assert dataset["column_count"] == 3

        # List
        datasets = await client.data.list()
        assert len(datasets) >= 1
        assert any(d["id"] == dataset["id"] for d in datasets)

        # Profile
        profile = await client.data.profile(dataset["id"])
        assert "columns" in profile
    finally:
        os.unlink(csv_path)
