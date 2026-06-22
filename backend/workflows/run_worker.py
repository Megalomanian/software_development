"""Temporal Worker entrypoint — executes ML training workflows."""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from backend.core.config import settings
from backend.workflows.training_workflow import TrainingWorkflow


async def main():
    client = await Client.connect(settings.temporal_host)
    worker = Worker(
        client,
        task_queue="ml-training-queue",
        workflows=[TrainingWorkflow],
    )
    print(f"Temporal Worker connected to {settings.temporal_host}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
