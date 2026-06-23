"""ML Platform Python SDK.

A clean Python client for the ML Platform API.
Covers: data → experiments → models → deployments → monitoring → auth → system.

Usage::

    from ml_platform import Client

    client = Client("http://localhost:8000", token="eyJ...")

    # Upload data
    dataset = await client.data.upload("data.csv")

    # Create and run experiment
    exp = await client.experiments.create(
        name="my-exp",
        dataset_id=dataset["id"],
        target_column="target",
        problem_type="classification",
    )
    result = await client.experiments.run_sklearn(exp["id"])

    # Register and deploy model
    model = await client.models.register("my-model", exp["id"])
    deployment = await client.deployments.create(model["id"])
"""

from __future__ import annotations

from ml_platform.auth import AuthAPI
from ml_platform.client import Client

__all__ = ["Client", "AuthAPI"]
