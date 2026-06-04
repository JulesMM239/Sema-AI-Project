from __future__ import annotations

import os
from typing import List, Dict

from sqlalchemy import create_engine, text


DB_URL = os.getenv("APP_DB_URL", "")


def fetch_corpus_rows(limit: int = 100000) -> List[Dict[str, str]]:
    """Fetch corpus rows from Postgres (corpus_items table).

    Returns a list of dicts: {"dialect": "KIV"|"KAT", "text": "..."}
    """
    if not DB_URL:
        return []

    eng = create_engine(DB_URL, pool_pre_ping=True)
    q = text(
        """
        SELECT dialect, text
        FROM corpus_items
        WHERE text IS NOT NULL
          AND length(text) > 0
        ORDER BY id ASC
        LIMIT :limit
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(q, {"limit": limit}).mappings().all()
    return [{"dialect": r["dialect"], "text": r["text"]} for r in rows]
