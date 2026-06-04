from redis import Redis
from rq import Queue
from app.config import settings

def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)

def get_queue(name: str = "training") -> Queue:
    return Queue(name, connection=get_redis(), default_timeout=60 * 60)
