import json
import importlib
import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
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
        self.shutdown_event = threading.Event()

        if client is not None:
            self.client = client
        else:
            if Valkey is None:
                # This path is taken if valkey is not installed and no client is provided.
                raise ImportError(
                    "Valkey client not provided and 'valkey' package not installed."
                )
            self.client = Valkey.from_url("valkey://localhost:6379")

        self.logger = logging.getLogger(self.__class__.__module__)
        self.logger.setLevel(logging.INFO)

    def _handle_shutdown(self, signum, frame):
        """
        Signal handler to initiate a graceful shutdown.
        """
        self.logger.info(
            "Shutdown signal received (SIG %s). Stopping job fetching...", signum
        )
        self.shutdown_event.set()

    def _fetch_job(self) -> Optional[Any]:
        """
        Fetches a job from the queues using a blocking pop.
        Respects the order of queues for priority.
        """
        if self.shutdown_event.is_set():
            return None
        queue_keys = [f"frontpunch:queue:{q}" for q in self.queues]
        # The timeout is set to 1 to prevent blocking indefinitely during shutdown.
        return self.client.brpop(queue_keys, timeout=1)

    def _execute_job(self, payload: str) -> None:
        """
        Deserializes and executes a job from a JSON payload.
        Handles JSON, schema, and import errors gracefully.
        """
        job_data = {}  # Ensure job_data is defined for error logging
        try:
            job_data = json.loads(payload)
            task_path = job_data["path"]
            task_args = job_data["args"]
        except json.JSONDecodeError:
            self.logger.error("Failed to decode job payload: %s", payload)
            return
        except KeyError as e:
            self.logger.error("Missing key in job payload: %s. Payload: %s", e, payload)
            return

        try:
            module_path, function_name = task_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            task_function = getattr(module, function_name)

            self.logger.info("Executing job: %s with args %s", task_path, task_args)
            if isinstance(task_args, list):
                task_function(*task_args)
            elif isinstance(task_args, dict):
                task_function(**task_args)
            else:
                self.logger.error(
                    "Invalid 'args' type for task %s: %s. Must be list or dict.",
                    task_path,
                    type(task_args),
                )
                return
            self.logger.info("Job %s completed successfully.", task_path)
        except (ImportError, AttributeError) as e:
            self.logger.error("Failed to import or find task '%s': %s", task_path, e)
        except Exception as e:
            self.logger.critical(
                "An unexpected error occurred during execution of task '%s': %s",
                task_path,
                e,
                exc_info=True,
            )

    def run(self):
        """
        Starts the worker, fetching and processing jobs until a shutdown is requested.
        """
        # Signal handlers can only be registered in the main thread.
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)

        self.logger.info(
            f"Worker starting. Concurrency: {self.concurrency}. Queues: {self.queues}"
        )

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            while not self.shutdown_event.is_set():
                job = self._fetch_job()
                if job:
                    _, payload = job
                    executor.submit(self._execute_job, payload.decode("utf-8"))

            self.logger.info(
                "Shutting down executor. Waiting for in-progress tasks to complete..."
            )
        self.logger.info("Worker has shut down.")
