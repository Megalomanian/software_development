"""In-memory training job queue with background worker.

Jobs are processed sequentially (FIFO). Status updates are
written to the Experiment record in the database.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingJob:
    experiment_id: str
    experiment_name: str
    position: int = 0
    status: JobStatus = JobStatus.QUEUED
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    username: str | None = None
    mlflow_run_id: str | None = None


class TrainingQueue:
    """Singleton FIFO queue with background worker."""

    _instance: TrainingQueue | None = None

    def __new__(cls) -> TrainingQueue:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._queue: list[TrainingJob] = []
            cls._instance._worker_task: asyncio.Task[Any] | None = None
            cls._instance._session_factory: async_sessionmaker[AsyncSession] | None = None
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    def configure(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Set the DB session factory (call once at startup)."""
        self._session_factory = session_factory

    async def enqueue(
        self, experiment_id: str, experiment_name: str,
        username: str | None = None,
    ) -> dict:
        """Add a training job to the queue."""
        async with self._lock:
            job = TrainingJob(
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                position=len(self._queue) + 1,
                username=username,
            )
            self._queue.append(job)
            logger.info("Enqueued %s (position %d, user=%s)", experiment_name, job.position, username)
            self._ensure_worker()
        return {
            "experiment_id": experiment_id,
            "position": job.position,
            "status": JobStatus.QUEUED,
        }

    def get_status(self) -> dict:
        """Get the full queue status with server resource info."""
        import psutil

        jobs = [
            {
                "experiment_id": j.experiment_id,
                "experiment_name": j.experiment_name,
                "position": j.position,
                "status": j.status,
                "added_at": str(j.added_at),
                "error": j.error,
                "username": j.username or "-",
                "mlflow_run_id": j.mlflow_run_id,
            }
            for j in self._queue
        ]
        running = next((j for j in jobs if j["status"] == JobStatus.RUNNING), None)
        pending = [j for j in jobs if j["status"] == JobStatus.QUEUED]

        # System resource info
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        return {
            "total": len(self._queue),
            "pending": len(pending),
            "running": running,
            "completed": len([j for j in jobs if j["status"] == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j["status"] == JobStatus.FAILED]),
            "jobs": jobs,
            "server": {
                "cpu_percent": cpu,
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 1),
                    "used_gb": round(mem.used / (1024**3), 1),
                    "available_gb": round(mem.available / (1024**3), 1),
                    "percent": mem.percent,
                },
            },
        }

    def _ensure_worker(self) -> None:
        """Start the background worker if not already running."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        """Background worker that processes jobs one at a time."""
        while True:
            job: TrainingJob | None = None
            async with self._lock:
                # Find first queued job
                for j in self._queue:
                    if j.status == JobStatus.QUEUED:
                        job = j
                        job.status = JobStatus.RUNNING
                        break

            if job is None:
                # All done
                break

            logger.info("Starting training: %s", job.experiment_name)
            try:
                await self._run_job(job)
                job.status = JobStatus.COMPLETED
                logger.info("Completed training: %s", job.experiment_name)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                logger.error("Training failed: %s — %s", job.experiment_name, e)

    async def _run_job(self, job: TrainingJob) -> None:
        """Execute a single training job using sklearn."""
        from backend.services.training_service import TrainingService

        if self._session_factory is None:
            raise RuntimeError("TrainingQueue not configured — call .configure() first")

        async with self._session_factory() as db:
            svc = TrainingService(db)

            # Update experiment status
            from backend.models_db.experiment import Experiment

            result = await db.execute(
                select(Experiment).where(Experiment.id == job.experiment_id)
            )
            exp = result.scalar_one_or_none()
            if exp:
                exp.status = "running"
                await db.commit()

            try:
                await svc.run_experiment_sklearn(job.experiment_id)
                if exp:
                    exp.status = "completed"
                    await db.commit()
            except Exception:
                if exp:
                    exp.status = "failed"
                    await db.commit()
                raise

    @classmethod
    async def reset(cls) -> None:
        """Reset the singleton (for testing).

        Clears the queue, cancels the worker, and awaits
        cancellation to ensure no stale DB sessions remain.
        """
        if cls._instance is None:
            return
        # Clear queue so worker loop exits naturally
        cls._instance._queue.clear()
        # Cancel and await worker task
        if cls._instance._worker_task and not cls._instance._worker_task.done():
            cls._instance._worker_task.cancel()
            try:
                await cls._instance._worker_task
            except asyncio.CancelledError:
                pass
        cls._instance = None


# Module-level convenience accessor
def get_queue() -> TrainingQueue:
    return TrainingQueue()
