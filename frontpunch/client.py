import redis
from typing import Optional

_redis_client: Optional[redis.Redis] = None


class ConfigurationError(Exception):
    """Raised when the library is not configured correctly."""
    pass


def configure(redis_url: str):
    """
    Configures the Frontpunch client with a Redis connection.

    Args:
        redis_url: The URL for the Redis server (e.g., "redis://localhost:6379/0").
    """
    global _redis_client
    # decode_responses=True is a good default for most string-based interactions
    _redis_client = redis.from_url(redis_url, decode_responses=True)


def get_client() -> redis.Redis:
    """
    Retrieves the configured Redis client.

    Returns:
        The configured redis.Redis instance.

    Raises:
        ConfigurationError: If the client has not been configured yet.
    """
    if _redis_client is None:
        raise ConfigurationError("Frontpunch not configured. Please call frontpunch.configure() first.")
    return _redis_client


def _reset_client():
    """For testing purposes only. Resets the global client."""
    global _redis_client
    _redis_client = None
