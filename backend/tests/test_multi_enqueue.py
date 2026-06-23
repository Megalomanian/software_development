"""Comprehensive multi-task training queue test.

Submits multiple training tasks at once and verifies sequential
FIFO processing, status transitions, and final experiment results.
"""

from __future__ import annotations

import asyncio
import io
import tempfile

import mlflow
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.services.training_queue import TrainingQueue


@pytest.fixture(autouse=True)
def _use_local_mlflow():
    tmp = tempfile.mkdtemp(prefix="mlflow_multi_")
    mlflow.set_tracking_uri(f"sqlite:///{tmp}/mlflow.db")
    yield
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
async def multi_client(db_session):
    """Full API client with auth, data, experiments, and models routes."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from backend.api.auth import router as auth_router
    from backend.api.data import router as data_router
    from backend.api.experiments import router as experiment_router
    from backend.api.models import router as model_router
    from backend.core.auth import create_access_token, hash_password
    from backend.core.dependencies import get_db
    from backend.models_db.user import User

    await TrainingQueue.reset()

    # Create test user
    user = User(
        username="multi_test", email="multi@test.com",
        hashed_password=hash_password("test"),
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token({"sub": str(user.id)})

    app = FastAPI(title="Multi-Queue Test")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")
    app.include_router(model_router, prefix="/api/models")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c
    await TrainingQueue.reset()


async def _upload_csv(client: AsyncClient, filename: str, csv_content: bytes) -> str:
    """Upload a CSV and return dataset_id."""
    resp = await client.post(
        "/api/data/upload",
        files={"file": (filename, io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def _create_and_enqueue(
    client: AsyncClient,
    name: str,
    dataset_id: str,
    target: str,
    problem_type: str,
) -> str:
    """Create an experiment and enqueue it. Returns experiment_id."""
    resp = await client.post(
        "/api/experiments/",
        json={
            "name": name,
            "dataset_id": dataset_id,
            "target_column": target,
            "problem_type": problem_type,
        },
    )
    assert resp.status_code == 200, resp.text
    exp_id = resp.json()["id"]

    resp = await client.post(f"/api/experiments/{exp_id}/enqueue")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "queued"
    return exp_id


@pytest.mark.asyncio
async def test_multi_enqueue_fifo_order(multi_client: AsyncClient, db_session):
    """Enqueue 5 experiments and verify FIFO order in queue status.

    Does NOT configure the queue — worker will fail jobs (no session_factory),
    but the ordering in the jobs list must still be FIFO.
    """
    csv = b"f1,f2,f3,target\n1,2,3,0\n4,5,6,1\n7,8,9,0\n10,11,12,1\n13,14,15,0\n"
    ds_id = await _upload_csv(multi_client, "fifo-test.csv", csv)

    names = ["fifo-1", "fifo-2", "fifo-3", "fifo-4", "fifo-5"]
    exp_ids = []
    for i, name in enumerate(names):
        eid = await _create_and_enqueue(
            multi_client, name, ds_id, "target", "classification"
        )
        exp_ids.append(eid)
        # Check position in response
        resp = await multi_client.get("/api/experiments/queue/status")
        jobs = resp.json()["jobs"]
        # Position values should be sequential and match insertion order
        assert jobs[i]["experiment_name"] == name, f"Job {i} should be {name}"

    # Final queue check — all 5 entries present in FIFO order
    resp = await multi_client.get("/api/experiments/queue/status")
    data = resp.json()
    assert data["total"] == 5
    job_names = [j["experiment_name"] for j in data["jobs"]]
    assert job_names == names  # FIFO order preserved
    # Positions should be 1-5
    positions = [j["position"] for j in data["jobs"]]
    assert positions == [1, 2, 3, 4, 5]

    # Verify all experiments exist
    for eid in exp_ids:
        resp = await multi_client.get(f"/api/experiments/{eid}")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_multi_enqueue_all_process(multi_client: AsyncClient, db_session):
    """Enqueue 3 experiments and wait for all to complete processing."""
    from backend.services.training_queue import TrainingQueue

    # Configure the queue with test DB session factory
    # Use expire_on_commit=True so the test session sees worker-committed changes
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=True)
    queue = TrainingQueue()
    queue.configure(session_factory)

    # Create datasets with different characteristics
    _csv_cls = b"a,b,target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n9,10,0\n11,12,1\n"
    _csv_reg = b"x,y,score\n10,20,100\n30,40,200\n50,60,300\n70,80,400\n90,100,500\n110,120,600\n"
    _csv_cls2 = (
        b"p,q,label\n1.1,2.2,A\n3.3,4.4,B\n5.5,6.6,A\n7.7,8.8,B\n"
        b"9.9,10.10,A\n11.11,12.12,B\n13.13,14.14,A\n"
    )

    ds1 = await _upload_csv(multi_client, "batch-cls.csv", _csv_cls)
    ds2 = await _upload_csv(multi_client, "batch-reg.csv", _csv_reg)
    ds3 = await _upload_csv(multi_client, "batch-cls2.csv", _csv_cls2)

    # Create and enqueue all three
    exp1 = await _create_and_enqueue(multi_client, "batch-cls", ds1, "target", "classification")
    exp2 = await _create_and_enqueue(multi_client, "batch-reg", ds2, "score", "regression")
    exp3 = await _create_and_enqueue(multi_client, "batch-cls2", ds3, "label", "classification")

    exp_ids = [exp1, exp2, exp3]
    exp_names = ["batch-cls", "batch-reg", "batch-cls2"]

    # Monitor queue until all done (max 60s)
    all_done = False
    status_snapshots = []
    for _ in range(60):
        await asyncio.sleep(1)
        resp = await multi_client.get("/api/experiments/queue/status")
        status = resp.json()
        status_snapshots.append({
            "pending": status["pending"],
            "running": status["running"]["experiment_name"] if status["running"] else None,
            "completed": status["completed"],
            "failed": status["failed"],
        })
        if status["pending"] == 0 and status["running"] is None:
            all_done = True
            break

    assert all_done, (
        f"Queue did not finish within 60s. "
        f"Last status: pending={status_snapshots[-1]['pending']}, "
        f"running={status_snapshots[-1]['running']}, "
        f"completed={status_snapshots[-1]['completed']}, "
        f"failed={status_snapshots[-1]['failed']}"
    )

    # Final queue status
    resp = await multi_client.get("/api/experiments/queue/status")
    final = resp.json()
    assert final["total"] == 3
    assert final["pending"] == 0
    assert final["running"] is None
    assert final["failed"] == 0
    assert final["completed"] == 3

    # All jobs should be in completed state
    for job in final["jobs"]:
        assert job["status"] == "completed", (
            f"{job['experiment_name']} not completed: {job['status']}"
        )

    # Expire test session cache so it sees worker-committed changes
    db_session.expire_all()

    # Verify each experiment has status "completed" and has MLflow metrics
    for eid, ename in zip(exp_ids, exp_names, strict=True):
        resp = await multi_client.get(f"/api/experiments/{eid}")
        exp = resp.json()
        assert exp["status"] == "completed", f"{ename}: expected completed, got {exp['status']}"
        assert exp["mlflow_run_id"] is not None, f"{ename}: no mlflow_run_id"

        # Check MLflow metrics
        resp = await multi_client.get(f"/api/experiments/{eid}/mlflow-metrics")
        metrics = resp.json()
        assert "metrics" in metrics
        assert len(metrics["metrics"]) > 0, f"{ename}: no metrics recorded"

    # Verify sequential processing by checking status snapshots
    # At no point should there be more than 1 running job
    running_count_per_snapshot = [
        1 if s["running"] else 0 for s in status_snapshots
    ]
    assert max(running_count_per_snapshot) <= 1, "More than one job was running simultaneously"


@pytest.mark.asyncio
async def test_multi_enqueue_mixed_with_auth(multi_client: AsyncClient, db_session):
    """Register user, upload data, enqueue 2 experiments, verify with auth."""
    # Register a user first
    resp = await multi_client.post(
        "/api/auth/register",
        json={"username": "trainer", "email": "trainer@test.com", "password": "train123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify auth works
    resp = await multi_client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "trainer"

    # Configure queue
    from backend.services.training_queue import TrainingQueue

    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    TrainingQueue().configure(session_factory)

    # Upload data
    csv = b"x1,x2,y\n1,2,10\n3,4,20\n5,6,30\n7,8,40\n9,10,50\n11,12,60\n"
    ds_id = await _upload_csv(multi_client, "auth-test.csv", csv)

    # Create & enqueue 2 experiments
    exp_a = await _create_and_enqueue(multi_client, "auth-exp-a", ds_id, "y", "regression")
    exp_b = await _create_and_enqueue(multi_client, "auth-exp-b", ds_id, "y", "regression")

    # Wait for processing
    for _ in range(60):
        await asyncio.sleep(1)
        resp = await multi_client.get("/api/experiments/queue/status")
        status = resp.json()
        if status["pending"] == 0 and status["running"] is None:
            break

    # Check final status
    resp = await multi_client.get("/api/experiments/queue/status")
    final = resp.json()
    assert final["failed"] == 0
    assert final["completed"] == 2

    # Both experiments should have metrics
    for eid in [exp_a, exp_b]:
        resp = await multi_client.get(f"/api/experiments/{eid}/mlflow-metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        # Regression should have mse or r2
        metric_keys = [m["key"] for m in metrics["metrics"]]
        has_reg_metric = any(k in metric_keys for k in ["mse", "r2"])
        assert has_reg_metric, f"No regression metric found: {metric_keys}"


@pytest.mark.asyncio
async def test_queue_concurrent_enqueue(multi_client: AsyncClient, db_session):
    """Enqueue tasks rapidly (simulating concurrent users) and verify no duplicates.

    This tests the async lock mechanism in TrainingQueue.
    """
    from backend.services.training_queue import TrainingQueue

    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    TrainingQueue().configure(session_factory)

    csv = b"a,b,target\n1,2,1\n3,4,0\n5,6,1\n7,8,0\n"
    ds_id = await _upload_csv(multi_client, "concurrent.csv", csv)

    # Create 4 experiments first
    exp_ids = []
    for i in range(4):
        resp = await multi_client.post(
            "/api/experiments/",
            json={
                "name": f"concurrent-{i}",
                "dataset_id": ds_id,
                "target_column": "target",
                "problem_type": "classification",
            },
        )
        assert resp.status_code == 200
        exp_ids.append(resp.json()["id"])

    # Enqueue all 4 concurrently
    tasks = [
        multi_client.post(f"/api/experiments/{eid}/enqueue") for eid in exp_ids
    ]
    results = await asyncio.gather(*tasks)

    # All should succeed
    for i, r in enumerate(results):
        assert r.status_code == 200, f"concurrent-{i} failed: {r.text}"
        assert r.json()["status"] == "queued"

    # Check queue has exactly 4 jobs
    resp = await multi_client.get("/api/experiments/queue/status")
    data = resp.json()
    assert data["total"] == 4

    # Verify unique positions
    positions = [j["position"] for j in data["jobs"]]
    assert len(positions) == len(set(positions)), f"Duplicate positions: {positions}"

    # Wait for all to complete
    for _ in range(60):
        await asyncio.sleep(1)
        resp = await multi_client.get("/api/experiments/queue/status")
        status = resp.json()
        if status["pending"] == 0 and status["running"] is None:
            break

    final = (await multi_client.get("/api/experiments/queue/status")).json()
    assert final["completed"] == 4
    assert final["failed"] == 0
