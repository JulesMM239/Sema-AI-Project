from __future__ import annotations

import os

from redis import Redis
from rq import Queue


def get_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    conn = Redis.from_url(redis_url)
    return Queue("train", connection=conn, default_timeout=60 * 60 * 12)
