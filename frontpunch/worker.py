import logging
from typing import Any, List, Optional


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
        self.client = client
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
