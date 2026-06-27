import redis
from urllib.parse import urlparse

# Module-level variable to hold the connection pool.
# This acts as a singleton.
_pool: redis.ConnectionPool = None

def configure(redis_url: str):
    """
    Configures the Redis connection pool.

    This function must be called before get_client(). It can be called multiple
    times to reconfigure the connection.

    Args:
        redis_url (str): The URL of the Redis server (e.g., "redis://localhost:6379/0").
                         Supports both redis:// and rediss:// schemes.

    Raises:
        ValueError: If the provided URL has an invalid scheme.
    """
    global _pool

    parsed_url = urlparse(redis_url)
    if parsed_url.scheme not in ('redis', 'rediss'):
        raise ValueError(f"Invalid Redis URL scheme: {parsed_url.scheme}")

    # If a pool already exists, disconnect it before creating a new one.
    if _pool:
        _pool.disconnect()

    _pool = redis.ConnectionPool.from_url(redis_url)

def get_client() -> redis.Redis:
    """
    Gets a Redis client from the connection pool.

    configure() must be called before this function.

    Returns:
        redis.Redis: A Redis client instance.

    Raises:
        RuntimeError: If the connection pool has not been configured.
    """
    if _pool is None:
        raise RuntimeError("Redis connection manager has not been configured. Call configure() first.")
    
    return redis.Redis(connection_pool=_pool)
