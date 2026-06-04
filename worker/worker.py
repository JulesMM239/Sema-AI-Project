import os
from rq import Worker, Queue, Connection
#from redis import Redis
import redis

# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


#def main():
    #redis_conn = Redis.from_url(REDIS_URL)
    
#    redis_conn = Redis(
#        host="localhost",
#        port=6379,
#        db=0
#    )
    
#   with Connection(redis_conn):
##        q = Queue("train")
#        w = Worker([q])
#        w.work(with_scheduler=True)

listen = ['high', 'default', 'low']

redis_url = os.getenv("REDIS_URL")
if redis_url:
    conn = redis.from_url(redis_url)
else:
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    conn = redis.Redis(host=redis_host, port=redis_port)
if __name__ == "__main__":
    #main()
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
