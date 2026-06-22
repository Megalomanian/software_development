# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MLOps platform for business analysts. Covers the full ML lifecycle: data ingestion → experiment training → model registry → deployment → inference monitoring. Users interact via a **Python SDK** (`ml_platform`), not a web UI. Swagger docs available at `/docs`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (Python 3.12+), async |
| SDK | **Python 3.12+** + **httpx** |
| Workflow engine | **Temporal** (task queue: `ml-training-queue`) |
| Experiment tracking | **MLflow** |
| Model serving | **Local in-memory** (default) + **Ray Serve** (fallback) |
| Databases | **PostgreSQL** (metadata) + **ClickHouse** (metrics/logs) |
| Object storage | **MinIO** (S3-compatible, accessed via **boto3**) |
| Monitoring | **Prometheus + Grafana** + **Evidently AI** |
| Package manager | **uv** (Tsinghua mirror in `uv.toml`) |

## Commands

```bash
# Backend — use uv for all package management
uv sync                                 # install all deps (uses Tsinghua mirror)
uv sync --no-dev                        # production install
uv run pytest                           # run all backend tests
uv run pytest backend/tests/ -k "upload"  # run tests matching keyword
uv run ruff check .                     # lint
uv run mypy backend/                    # type check

# SDK
cd sdk
uv sync                                 # install SDK deps
uv run ruff check ml_platform/          # lint SDK
uv run pytest                           # integration tests (needs API running)

# Infrastructure (Docker Compose)
docker compose up -d                    # start all 8 services
docker compose up -d postgres minio mlflow  # start essentials
docker compose down                     # stop all
```

## Architecture

```
ML Platform SDK  →  backend/ API (FastAPI)  →  Temporal workflows
                       ↓           ↓                ↓
                  PostgreSQL    MinIO/S3        MLflow / Ray Serve
                       ↓
                  ClickHouse  ←  Prometheus  ←  API metrics
```

### API route layout

All routes registered under `/api/` in `backend/main.py`:

| Prefix | Tag | Purpose |
|--------|-----|---------|
| `/api/data` | data | Dataset upload, list, profile |
| `/api/experiments` | experiments | Experiment CRUD, run, run-sklearn, MLflow metrics |
| `/api/models` | models | Model registry, promote, register from experiment |
| `/api/deployments` | deployments | Deploy lifecycle, stop, predict |
| `/api/monitoring` | monitoring | Deployment metrics, drift detection |
| `/api/health` | — | Health check |

**API conventions:**
- Request bodies are plain `dict`, not Pydantic models — validated manually in services
- ORM objects are returned directly from endpoints (no response schemas)
- Standard CRUD patterns: `GET /` (list with `offset`/`limit`), `GET /{id}`, `POST /` (create)
- Special actions: `POST /{id}/run`, `POST /{id}/stop`, `POST /{id}/predict`, `POST /{id}/promote`

### Backend structure

- `backend/main.py` — FastAPI app entry, CORS (allow all origins), Prometheus instrumentator, router registration
- `backend/core/config.py` — single `Settings` class via pydantic-settings, env vars prefixed with `MLP_`
- `backend/core/dependencies.py` — `create_async_engine` + `async_sessionmaker`, yields sessions via `get_db()` generator
- `backend/core/middleware.py` — `InferenceLoggingMiddleware`: intercepts `/api/deployments/{id}/predict`, logs latency/errors to DB (fire-and-forget)
- `backend/api/*.py` — route handlers (thin: parse params, call service, return result)
- `backend/services/*.py` — business logic, instantiated per-request with `AsyncSession`:
  - `data_service.py` — CSV upload, pandas profiling
  - `training_service.py` — experiment CRUD, sklearn training (RandomForest/LogisticRegression/LinearRegression), MLflow tracking
  - `model_service.py` — model registry, version promotion, registration from experiment
  - `deployment_service.py` — deployment lifecycle, defers to `RayServeManager`
  - `monitoring_service.py` — aggregates inference logs, z-score drift detection
  - `local_serving.py` — in-memory model registry, loads from MLflow, serves predictions directly
  - `ray_serve_manager.py` — fallback: generates deploy scripts to `/tmp/`, runs via `subprocess`
- `backend/models_db/*.py` — SQLAlchemy ORM models
- `backend/workflows/` — Temporal workflow + worker entrypoint

### ORM base pattern

All models inherit from `Base` (declarative base) + `TimestampMixin`:

```python
class TimestampMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- All PKs are UUID strings, not auto-increment integers
- Foreign keys reference `String(36)` columns

Models: `Dataset` → `DatasetColumn`, `Experiment` (FK → datasets), `ModelVersion` (FK → experiments), `Deployment` (FK → model_versions), `InferenceLog`

### SDK structure

```
sdk/ml_platform/
├── __init__.py          # exports Client
├── client.py            # Client class — wraps httpx.AsyncClient, each domain as property
├── data.py              # DataAPI — upload, list, get, profile
├── experiments.py       # ExperimentsAPI — CRUD, run, run_sklearn, get_metrics
├── models.py            # ModelsAPI — list, get, register, promote
├── deployments.py       # DeploymentsAPI — list, get, create, stop, predict
└── monitoring.py        # MonitoringAPI — get_metrics, get_drift
```

### Key patterns

- **DB**: All access is async (asyncpg + SQLAlchemy async sessions). Services receive `AsyncSession` in constructor.
- **Config**: Single `Settings` instance in `backend.core.config`, env vars with `MLP_` prefix.
- **DI**: FastAPI `Depends(get_db)` yields `AsyncSession` per request; services created inline.
- **SDK data flow**: `Client` wraps `httpx.AsyncClient`; each domain module gets the shared client; context manager support via `async with`.
- **Error handling**: Services raise `HTTPException`; middleware silently catches logging errors.
- **No migrations**: ORM models defined but no Alembic migration scripts yet.

## Testing

- **Database**: Tests use **SQLite in-memory** (`sqlite+aiosqlite:///:memory:`) — not PostgreSQL. Tables cleaned between tests.
- **HTTP client**: `httpx.AsyncClient` with `ASGITransport` — no server needed for backend tests.
- **DI override**: `app.dependency_overrides[get_db]` injects test session.
- **SDK tests**: Integration tests require a running API server (skip by default unless `CI=true`).

## Environment Variables

All prefixed with `MLP_`:

| Variable | Default |
|----------|---------|
| `MLP_DATABASE_URL` | `postgresql+asyncpg://mlp:mlp@localhost:5432/mlp` |
| `MLP_CLICKHOUSE_URL` | `http://localhost:8123` |
| `MLP_MLFLOW_TRACKING_URI` | `http://localhost:5000` |
| `MLP_MINIO_ENDPOINT` | `localhost:9000` |
| `MLP_MINIO_ACCESS_KEY` | `minioadmin` |
| `MLP_MINIO_SECRET_KEY` | `minioadmin` |
| `MLP_MINIO_BUCKET` | `ml-platform` |
| `MLP_TEMPORAL_HOST` | `localhost:7233` |
| `MLP_RAY_ADDRESS` | `auto` |
| `MLP_DEBUG` | `false` |
