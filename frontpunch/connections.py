import redis

class ConnectionManager:
    """Manages Redis connections."""
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._connection_pool = None

    def get_connection(self):
        """
        Returns a Redis connection from the connection pool.
        Creates the pool if it doesn't exist.
        """
        if self._connection_pool is None:
            self._connection_pool = redis.ConnectionPool.from_url(self.redis_url)
        return redis.Redis(connection_pool=self._connection_pool)
