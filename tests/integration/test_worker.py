import json
import threading
import unittest
from unittest.mock import Mock, patch

from frontpunch.worker import Worker
# Import test tasks and state management functions
from frontpunch.test_tasks import (
    reset_task_events,
    COMPLETED_TASKS,
    TASK_STARTED,
    FINISH_TASK,
)

class TestWorkerIntegrationShutdown(unittest.TestCase):
    def setUp(self):
        """
        Reset task state before each test.
        """
        reset_task_events()
        self.mock_client = Mock()
        self.worker = Worker(queues=["default"], concurrency=1, client=self.mock_client)

    def test_graceful_shutdown(self):
        """
        Tests that the worker shuts down gracefully.
        - It should stop fetching new jobs after a shutdown signal.
        - It should wait for in-progress jobs to complete.
        - It should exit its run loop.
        """
        job_payload = {
            "path": "frontpunch.test_tasks.long_running_task",
            "args": ["task1"],
        }
        encoded_payload = json.dumps(job_payload).encode("utf-8")

        # Configure the mock client's brpop
        # 1. Return the long-running job.
        # 2. Return None to simulate timeout during shutdown.
        self.mock_client.brpop.side_effect = [
            (b"frontpunch:queue:default", encoded_payload),
            None,
        ]

        # Run the worker in a separate thread
        worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        worker_thread.start()

        # 1. Wait for the worker to pick up the job and start executing it.
        started = TASK_STARTED.wait(timeout=2)
        self.assertTrue(started, "Task did not start in time.")

        # 2. While the job is running, trigger the shutdown.
        with patch.object(self.worker, 'logger') as mock_logger:
            self.worker._handle_shutdown(None, None)
            self.assertTrue(self.worker._shutdown)

            # 3. Allow the in-progress job to complete.
            FINISH_TASK.set()

            # 4. Wait for the worker thread to terminate.
            worker_thread.join(timeout=3)
            self.assertFalse(worker_thread.is_alive(), "Worker thread did not terminate.")

            # 5. Verify the first job completed.
            self.assertEqual(COMPLETED_TASKS, ["task1"])
            # brpop should be called twice: once for the job, and once after shutdown
            # where it times out and returns None, causing the loop to exit.
            self.assertEqual(self.mock_client.brpop.call_count, 2)

            # 6. Verify shutdown logs
            mock_logger.info.assert_any_call("Shutdown signal received. Stopping worker gracefully...")
            mock_logger.info.assert_any_call("Shutting down executor. Waiting for in-progress jobs to complete...")


if __name__ == '__main__':
    unittest.main()
