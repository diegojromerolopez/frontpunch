import os
from redis import Redis

class RedisConnector:
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            redis_host = os.environ.get("REDIS_HOST", "localhost")
            redis_port = int(os.environ.get("REDIS_PORT", 6379))
            redis_db = int(os.environ.get("REDIS_DB", 0))
            cls._connection = Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
        return cls._connection
