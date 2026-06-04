from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class DatasetRevision(Base):
    __tablename__ = "dataset_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="default")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|final
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    glossary_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    corpus_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_labels_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sha256

class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(120), index=True)
    dataset_revision_id: Mapped[int] = mapped_column(ForeignKey("dataset_revisions.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|success|failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)

    produced_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset_revision = relationship("DatasetRevision")

class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)  # e.g. v1, v2
    dataset_revision_id: Mapped[int] = mapped_column(ForeignKey("dataset_revisions.id"))
    artifact_path: Mapped[str] = mapped_column(Text)
    meta_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    dataset_revision = relationship("DatasetRevision")
