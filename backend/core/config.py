from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "MLP_", "extra": "ignore"}

    # Database — defaults to SQLite for local dev; set MLP_DATABASE_URL for PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./mlp.db"
    clickhouse_url: str = "http://localhost:8123"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ml-platform"

    # MLflow — defaults to local SQLite; set MLP_MLFLOW_TRACKING_URI for server
    mlflow_tracking_uri: str = "sqlite:///./mlflow.db"

    # Temporal
    temporal_host: str = "localhost:7233"

    # Ray
    ray_address: str = "auto"

    # Auth (JWT)
    jwt_secret: str = "change-me-in-production-use-a-strong-random-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # App
    app_name: str = "ML Platform"
    debug: bool = False


settings = Settings()
