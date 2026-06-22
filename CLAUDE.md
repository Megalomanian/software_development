# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Low-code MLOps platform for business analysts. Covers the full ML lifecycle: data ingestion → feature engineering → model training → deployment → inference monitoring. Users interact via a drag-and-drop visual pipeline editor (React Flow) without writing code.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (Python 3.12+), async |
| Frontend | **Next.js 15 + React 19**, TypeScript |
| UI | **Tailwind CSS**, **lucide-react** icons |
| Pipeline editor | **@xyflow/react** (React Flow v12) |
| Workflow engine | **Temporal** |
| Experiment tracking | **MLflow** |
| Model serving | **Ray Serve** |
| Databases | **PostgreSQL** (metadata) + **ClickHouse** (metrics/logs) |
| Object storage | **MinIO** (S3-compatible) |
| Monitoring | **Prometheus + Grafana** + **Evidently AI** |

## Commands

```bash
# Python — use uv for all package management
uv sync                    # install all deps
uv sync --no-dev           # production install
uv run pytest              # run tests
uv run ruff check .        # lint
uv run mypy backend/       # type check

# Frontend
cd frontend
npm run dev                # start dev server on :3000
npm run build              # production build
npm run lint               # lint

# Infrastructure (Docker Compose)
docker compose up -d           # start all services
docker compose up -d postgres minio mlflow  # start essentials
docker compose down            # stop all
```

## Architecture

```
frontend/  →  backend/ API (FastAPI)  →  Temporal workflows
               ↓           ↓                ↓
          PostgreSQL    MinIO/S3        MLflow / Ray Serve
               ↓
          ClickHouse  ←  Prometheus  ←  API metrics
```

### Backend structure

- `backend/main.py` — FastAPI app entry, CORS, Prometheus instrumentator, router registration
- `backend/core/config.py` — pydantic-settings, env vars prefixed with `MLP_`
- `backend/core/dependencies.py` — async SQLAlchemy session factory for FastAPI DI
- `backend/core/middleware.py` — inference logging middleware (latency, errors, request logging)
- `backend/api/*.py` — route handlers (data, experiments, models, deployments, monitoring)
- `backend/services/*.py` — business logic layer:
  - `data_service.py` — CSV upload, auto-profiling (pandas describe, histograms)
  - `training_service.py` — experiment CRUD, sklearn execution, MLflow tracking
  - `model_service.py` — model registry, version promotion, registration from experiments
  - `deployment_service.py` — deployment lifecycle, Ray Serve integration
  - `monitoring_service.py` — metrics aggregation, drift detection (z-score), inference logging
  - `ray_serve_manager.py` — Ray Serve deploy/stop/predict via subprocess scripts
- `backend/models_db/*.py` — SQLAlchemy ORM (Dataset, DatasetColumn, Experiment, PipelineNode, PipelineEdge, ModelVersion, Deployment, InferenceLog)
- `backend/workflows/` — Temporal workflow definitions + worker entrypoint

### Frontend structure

- `app/` — Next.js App Router pages (data, experiments, models, deployments, monitoring)
- `components/layout/Sidebar.tsx` — persistent sidebar navigation
- `components/pipeline-editor/` — React Flow-based drag-and-drop DAG editor
- `lib/api.ts` — typed fetch wrapper around the FastAPI backend

### Key patterns

- All DB access is async (asyncpg + SQLAlchemy async sessions)
- Config via env vars with `MLP_` prefix, read through `backend.core.config.settings`
- Services are instantiated per-request with the DB session, no global state
- Frontend uses server components by default, client components only where interactivity needed ('use client')

## Environment Variables

Set via `.env` or directly in Docker Compose. All prefixed with `MLP_`:

| Variable | Default |
|----------|---------|
| `MLP_DATABASE_URL` | `postgresql+asyncpg://mlp:mlp@localhost:5432/mlp` |
| `MLP_MLFLOW_TRACKING_URI` | `http://localhost:5000` |
| `MLP_MINIO_ENDPOINT` | `localhost:9000` |
| `MLP_TEMPORAL_HOST` | `localhost:7233` |
