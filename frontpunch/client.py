import redis
from .exceptions import ConnectionError
from .connections import ConnectionManager

def _get_queue_key(queue_name: str) -> str:
    """Returns the Redis key for a given queue name."""
    return f"frontpunch:queue:{queue_name}"

class Client:
    """
    Frontpunch client for enqueuing jobs.
    """
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    def _enqueue(self, queue_name: str, payload: str):
        """
        Internal function to enqueue a job.

        Args:
            queue_name: The name of the queue.
            payload: The serialized JSON payload of the job.

        Raises:
            ConnectionError: If a connection to Redis cannot be established.
        """
        try:
            conn = self.connection_manager.get_connection()
            queue_key = _get_queue_key(queue_name)
            conn.lpush(queue_key, payload)
        except redis.exceptions.ConnectionError as e:
            raise ConnectionError("Failed to connect to Redis") from e
