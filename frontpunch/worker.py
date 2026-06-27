import json
import importlib
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

    def _execute_job(self, payload: str) -> None:
        """
        Deserializes and executes a job from a JSON payload.

        Handles JSON decoding, key errors for missing payload fields,
        and import errors for the task function. Errors are logged,
        but the worker thread is not crashed.
        """
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
            task_function(*task_args)
            self.logger.info("Job %s completed successfully.", task_path)
        except (ImportError, AttributeError) as e:
            # This handles both module not found and function not found in module.
            self.logger.error("Failed to import or find task '%s': %s", task_path, e)
        except Exception as e:
            # A broad exception to catch errors within the executed task itself.
            self.logger.critical(
                "An unexpected error occurred during execution of task '%s': %s",
                task_path,
                e,
                exc_info=True,
            )

    def _execute_job(self, payload: str) -> None:
        """
        Deserializes and executes a job from a JSON payload.
        Handles JSON, schema, and import errors gracefully.
        """
        try:
            job_data = json.loads(payload)
            path = job_data["path"]
            args = job_data["args"]

            module_path, func_name = path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            # Assuming args is a dict for keyword arguments.
            func(**args)
        except json.JSONDecodeError:
            self.logger.error("Failed to decode JSON payload: %s", payload)
        except KeyError as e:
            self.logger.error("Missing key in job payload: %s. Payload: %s", e, payload)
        except (ImportError, AttributeError) as e:
            # At this point, job_data and job_data['path'] are guaranteed to exist.
            self.logger.error("Failed to import or find function '%s': %s", job_data["path"], e)
