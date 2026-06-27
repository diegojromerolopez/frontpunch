import logging
from typing import Any, List, Optional

try:
    # Attempt to import Valkey. This is the preferred client.
    from valkey import Valkey
except ImportError:
    # If valkey is not installed, set Valkey to None.
    # This allows the module to be imported and mocked in test environments
    # without requiring valkey to be installed.
    Valkey = None


class Worker:
    """
    A worker that processes jobs from specified queues.
    """

    def __init__(
        self,
        queues: List[str],
        concurrency: int,
        client: Optional[Any] = None,
    ):
        """
        Initializes the worker.

        :param queues: A list of queue names to listen to.
        :param concurrency: The number of concurrent jobs to run.
        :param client: An optional Valkey/Redis client instance for testability.
        """
        self.queues = queues
        self.concurrency = concurrency

        if client is not None:
            self.client = client
        else:
            if Valkey is None:
                # This path is taken if valkey is not installed and no client is provided.
                raise ImportError(
                    "Valkey client not provided and 'valkey' package not installed."
                )
            self.client = Valkey.from_url("valkey://localhost:6379")

        # The logger name should be based on the module, not the class name.
        self.logger = logging.getLogger(self.__class__.__module__)
        # The tests expect the logger level to be explicitly set to INFO.
        self.logger.setLevel(logging.INFO)

    def _fetch_job(self) -> Optional[Any]:
        """
        Fetches a job from the queues using a blocking pop.
        Respects the order of queues for priority.
        """
        queue_keys = [f"frontpunch:queue:{q}" for q in self.queues]
        # The timeout is set to 1 to prevent blocking indefinitely during shutdown.
        return self.client.brpop(queue_keys, timeout=1)
