import json
import time


class Worker:
    def __init__(self, redis_client, queues, tasks):
        self.redis_client = redis_client
        self.queues = queues
        self.tasks = tasks
        self.running = False

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculates the delay for the next retry using exponential backoff.
        Formula: delay = 15 + (retry_count * 10) + (retry_count**4)
        """
        delay = 15 + (retry_count * 10) + (retry_count**4)
        return float(delay)

    def _handle_job_failure(self, payload: dict, exception: Exception):
        """Handles a failed job by either rescheduling or moving to DLQ."""
        retry_count = payload.get("retry_count", 0)
        max_retries = payload.get("max_retries", 0)

        payload["error_class"] = exception.__class__.__name__
        payload["error_message"] = str(exception)

        if max_retries > 0 and retry_count < max_retries:
            # We have retries available.
            payload["retry_count"] = retry_count + 1
            delay = self._calculate_backoff_delay(payload["retry_count"])
            scheduled_time = time.time() + delay
            self.redis_client.zadd(
                "frontpunch:scheduled", {json.dumps(payload): scheduled_time}
            )
        else:
            # No retries left or retries are disabled.
            # Move to the dead-letter queue.
            self.redis_client.rpush("frontpunch:dead", json.dumps(payload))

    def run(self):
        self.running = True
        while self.running:
            try:
                _queue, job_payload_str = self.redis_client.blpop(self.queues)
            except StopIteration:
                # This is raised by mocks in tests to stop the loop.
                raise
            except Exception:
                # Could be a Redis connection error. Wait a bit and retry.
                time.sleep(1)
                continue

            if not job_payload_str:
                continue

            payload = json.loads(job_payload_str)
            task_name = payload.get("task")
            task_func = self.tasks.get(task_name)

            if not task_func:
                # If task is not found, we could move it to dead-letter queue.
                # For now, just skipping as per original logic.
                continue

            try:
                args = payload.get("args", [])
                if isinstance(args, dict):
                    task_func(**args)
                else:
                    task_func(*args)
            except Exception as e:
                # We do not catch BaseException, so things like KeyboardInterrupt
                # will still stop the worker.
                self._handle_job_failure(payload, e)
