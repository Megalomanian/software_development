from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models_db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models_db.dataset import Dataset
    from backend.models_db.model import ModelVersion


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id"), nullable=True
    )
    mlflow_run_id: Mapped[str] = mapped_column(String(255), nullable=True)
    pipeline_definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_column: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    dataset: Mapped["Dataset | None"] = relationship(back_populates="experiments")


class PipelineNode(Base, TimestampMixin):
    __tablename__ = "pipeline_nodes"

    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)


class PipelineEdge(Base, TimestampMixin):
    __tablename__ = "pipeline_edges"

    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
