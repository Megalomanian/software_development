from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models_db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models_db.experiment import Experiment


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    experiments: Mapped[list[Experiment]] = relationship(back_populates="dataset")


class DatasetColumn(Base, TimestampMixin):
    __tablename__ = "dataset_columns"

    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dtype: Mapped[str] = mapped_column(String(50), nullable=False)
    null_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    null_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    unique_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    std: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_val: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_val: Mapped[float | None] = mapped_column(Float, nullable=True)
    histogram: Mapped[str | None] = mapped_column(Text, nullable=True)
