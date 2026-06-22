from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models_db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id"), nullable=True
    )
    mlflow_model_uri: Mapped[str] = mapped_column(String(1024), nullable=True)
    framework: Mapped[str] = mapped_column(String(50), nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="registered")


class Deployment(Base, TimestampMixin):
    __tablename__ = "deployments"

    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="deploying")
    ray_serve_app: Mapped[str] = mapped_column(String(255), nullable=True)
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    traffic_percent: Mapped[int] = mapped_column(Integer, default=100)


class InferenceLog(Base, TimestampMixin):
    __tablename__ = "inference_logs"

    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
