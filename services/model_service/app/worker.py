from __future__ import annotations
import time
from rq import Worker
from app.queue import get_redis
from app.config import settings

def wait_for_redis(retries: int = 60, sleep_s: float = 1.0):
    r = get_redis()
    for _ in range(retries):
        try:
            r.ping()
            return
        except Exception:
            time.sleep(sleep_s)
    raise RuntimeError("Redis not reachable")

def main():
    wait_for_redis()
    w = Worker(["training"], connection=get_redis())
    w.work(with_scheduler=False)

if __name__ == "__main__":
    main()
