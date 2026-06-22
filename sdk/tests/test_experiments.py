"""Experiments API integration tests."""

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
async def test_full_experiment_flow(client: Client):
    """End-to-end: upload data → create experiment → run → get metrics."""
    # 1. Upload data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("f1,f2,target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n")
        csv_path = f.name

    try:
        dataset = await client.data.upload(csv_path)

        # 2. Create experiment
        exp = await client.experiments.create(
            name="sdk-test-exp",
            dataset_id=dataset["id"],
            target_column="target",
            problem_type="classification",
        )
        assert exp["name"] == "sdk-test-exp"
        assert exp["status"] == "pending"

        # 3. Run experiment
        result = await client.experiments.run(exp["id"])
        assert result["status"] == "completed"
        assert "mlflow_run_id" in result

        # 4. Get MLflow metrics
        metrics = await client.experiments.get_metrics(exp["id"])
        assert "metrics" in metrics
        assert "params" in metrics
    finally:
        os.unlink(csv_path)
