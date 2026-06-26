import redis

class RedisConnectionManager:
    """
    Manages a Redis connection pool.

    This class is designed to be instantiated once and shared across the application
    to provide Redis connections, supporting dependency injection.
    It handles secure (rediss://) and insecure (redis://) connections.
    """
    def __init__(self, redis_url: str):
        """
        Initializes the connection manager and creates a connection pool.

        Args:
            redis_url: The URL of the Redis server (e.g., "redis://localhost:6379/0"
                       or "rediss://user:password@host:port/0").
        """
        if not redis_url:
            raise ValueError("redis_url cannot be empty.")
        # decode_responses=True is a common setting to get strings from Redis.
        self._pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)

    def get_connection(self) -> redis.Redis:
        """
        Gets a Redis client connection from the pool.

        Returns:
            A redis.Redis client instance.
        """
        return redis.Redis(connection_pool=self._pool)
