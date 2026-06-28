import unittest
from unittest.mock import MagicMock
import threading
import time
import json
import signal
import logging

from frontpunch.worker import Worker
import frontpunch.test_tasks

# Added for the new integration test
try:
    from valkey import Valkey
except ImportError:
    Valkey = None

class TestWorkerGracefulShutdown(unittest.TestCase):

    def setUp(self):
        # Guideline 19: Ensure logging is enabled for assertLogs
        logging.disable(logging.NOTSET)
        self.mock_client = MagicMock()
        self.worker = Worker(queues=['test'], concurrency=2, client=self.mock_client)
        # Suppress console output unless using assertLogs
        self.worker.logger.propagate = False
        # Clear the global list used by test tasks
        frontpunch.test_tasks.GLOBAL_RECORD_LIST.clear()

    def tearDown(self):
        frontpunch.test_tasks.GLOBAL_RECORD_LIST.clear()

    def test_graceful_shutdown_allows_tasks_to_complete(self):
        """
        Verify that a graceful shutdown stops fetching new jobs but allows
        in-progress jobs to complete.
        """
        task_started_event = threading.Event()
        unblock_brpop_event = threading.Event()

        long_task_payload = json.dumps({
            "path": "frontpunch.test_tasks.recording_task",
            "args": [0.2]
        }).encode('utf-8')

        original_execute_job = self.worker._execute_job
        def execute_job_wrapper(payload):
            task_started_event.set()
            return original_execute_job(payload)
        self.worker._execute_job = execute_job_wrapper

        # We use a callable for side_effect to control the mock's behavior
        # across multiple calls within the worker's loop.
        brpop_calls = 0
        def brpop_side_effect_handler(*args, **kwargs):
            nonlocal brpop_calls
            brpop_calls += 1
            if brpop_calls == 1:
                # The first call to brpop returns the long-running task.
                return (b'frontpunch:queue:test', long_task_payload)

            # The second call simulates blocking until the test signals it to continue.
            # This mimics waiting for a job that never arrives because we're shutting down.
            unblock_brpop_event.wait(timeout=2)
            # After being unblocked, it returns None, simulating a brpop timeout.
            return None

        self.mock_client.brpop.side_effect = brpop_side_effect_handler

        worker_thread = threading.Thread(target=self.worker.run)
        
        with self.assertLogs('frontpunch.worker', level='INFO') as cm:
            worker_thread.start()

            started = task_started_event.wait(timeout=2)
            self.assertTrue(started, "The long-running task did not start in time.")
            
            # The task appends to the list before sleeping, but we wait briefly
            # to make the assertion against the list more robust.
            time.sleep(0.05)
            self.assertEqual(len(frontpunch.test_tasks.GLOBAL_RECORD_LIST), 1)

            # Simulate receiving a shutdown signal and unblock the worker
            self.worker._handle_shutdown(signal.SIGTERM, None)
            unblock_brpop_event.set()
            
            # The worker should shut down gracefully, waiting for the task to finish.
            worker_thread.join(timeout=2)

            self.assertFalse(worker_thread.is_alive(), "Worker thread did not terminate.")

        # Verify that no new tasks were started after shutdown was initiated
        self.assertEqual(len(frontpunch.test_tasks.GLOBAL_RECORD_LIST), 1)
        self.assertEqual(self.mock_client.brpop.call_count, 2)

        # Verify the shutdown log messages
        log_output = "".join(cm.output)
        self.assertIn("Shutdown signal received", log_output)
        self.assertIn("Shutting down executor. Waiting for in-progress tasks to complete...", log_output)
        self.assertIn("Worker has shut down.", log_output)


@unittest.skipIf(Valkey is None, "valkey package not installed")
class TestWorkerPrioritizedExecution(unittest.TestCase):

    def setUp(self):
        # Use a real Valkey client. The test runner should provide the service.
        self.client = Valkey.from_url("valkey://localhost:6379")
        try:
            self.client.ping()
        except Exception as e:
            self.fail(f"Valkey server not available at localhost:6379. Error: {e}")

        self.queues = ['critical', 'default']
        self.queue_keys = [f"frontpunch:queue:{q}" for q in self.queues]

        # Clean up before the test
        self.client.delete(*self.queue_keys)
        frontpunch.test_tasks.GLOBAL_RECORD_LIST.clear()

    def tearDown(self):
        # Clean up after the test
        self.client.delete(*self.queue_keys)
        frontpunch.test_tasks.GLOBAL_RECORD_LIST.clear()
        self.client.close()

    def test_prioritized_queue_execution(self):
        """
        AC-1: Verify that jobs from a high-priority queue are processed before
        jobs from a low-priority queue.
        """
        # 1. Push one job to `frontpunch:queue:critical` and one to `frontpunch:queue:default`.
        # We push the default job first to ensure priority is respected regardless of insertion order.
        default_job_payload = json.dumps({
            "path": "frontpunch.test_tasks.recording_task",
            "args": ["default_job"]
        })
        critical_job_payload = json.dumps({
            "path": "frontpunch.test_tasks.recording_task",
            "args": ["critical_job"]
        })

        self.client.lpush('frontpunch:queue:default', default_job_payload)
        self.client.lpush('frontpunch:queue:critical', critical_job_payload)

        # 2. Run the worker with `--queues critical,default`.
        # We'll use a thread for simplicity in testing.
        worker = Worker(queues=self.queues, concurrency=1, client=self.client)
        # Suppress console output for cleaner test logs
        worker.logger.propagate = False
        
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()

        # Wait for both jobs to be processed.
        timeout = 5  # seconds
        start_time = time.time()
        while len(frontpunch.test_tasks.GLOBAL_RECORD_LIST) < 2:
            time.sleep(0.01)
            if time.time() - start_time > timeout:
                self.fail(
                    "Worker did not process both jobs within the timeout period. "
                    f"Processed: {frontpunch.test_tasks.GLOBAL_RECORD_LIST}"
                )

        # Now that jobs are done, gracefully shut down the worker.
        worker.shutdown_event.set()
        worker_thread.join(timeout=2)

        self.assertFalse(worker_thread.is_alive(), "Worker thread did not terminate.")

        # 3. Verify that the job from the `critical` queue is processed first.
        self.assertEqual(len(frontpunch.test_tasks.GLOBAL_RECORD_LIST), 2)
        self.assertEqual(
            frontpunch.test_tasks.GLOBAL_RECORD_LIST,
            ['critical_job', 'default_job']
        )
