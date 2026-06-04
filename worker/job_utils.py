from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import create_engine, text


DB_URL = os.getenv("APP_DB_URL", "")


def update_job(job_id: int, status: str, notes: str | None = None, model_version: str | None = None):
    """Update training_jobs row (created by API) with new status/notes."""
    if not DB_URL:
        return
    eng = create_engine(DB_URL, pool_pre_ping=True)
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE training_jobs
                SET status=:status,
                    notes=COALESCE(:notes, notes),
                    model_version=COALESCE(:model_version, model_version),
                    updated_at=:updated_at
                WHERE id=:id
                """
            ),
            {
                "id": job_id,
                "status": status,
                "notes": notes,
                "model_version": model_version,
                "updated_at": datetime.utcnow(),
            },
        )


def fetch_job(job_id: int) -> dict | None:
    if not DB_URL:
        return None
    eng = create_engine(DB_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT id, status, model_version, notes FROM training_jobs WHERE id=:id"),
            {"id": job_id},
        ).mappings().first()
    return dict(row) if row else None