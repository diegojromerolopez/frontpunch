import unittest
from unittest.mock import MagicMock
import threading
import time
import json
import logging
from multiprocessing import Manager

from frontpunch.worker import Worker
# We need to import the module so the worker can find the task
from frontpunch import test_tasks

# Suppress logging for cleaner test output
logging.disable(logging.CRITICAL)

class TestWorkerConcurrency(unittest.TestCase):

    def setUp(self):
        # Ensure logging is disabled for each test
        logging.disable(logging.CRITICAL)

    def test_run_executes_jobs_concurrently(self):
        """
        Verify that the worker runs multiple jobs concurrently using ThreadPoolExecutor.
        """
        # 1. Setup
        mock_client = MagicMock()
        manager = Manager()
        execution_times = manager.list()  # Thread-safe list for results

        # Patch the global list in the tasks module so our task can append to it.
        # This is a common pattern for testing side-effects in concurrent code.
        original_list = test_tasks.GLOBAL_RECORD_LIST
        test_tasks.GLOBAL_RECORD_LIST = execution_times
        self.addCleanup(setattr, test_tasks, 'GLOBAL_RECORD_LIST', original_list)

        # Create two jobs that will run for 0.2 seconds each
        job_duration = 0.2
        job1_payload = json.dumps({
            "path": "frontpunch.test_tasks.recording_task",
            "args": {"duration": job_duration}
        })
        job2_payload = json.dumps({
            "path": "frontpunch.test_tasks.recording_task",
            "args": {"duration": job_duration}
        })

        # Mock brpop to return two jobs, then None to simulate an empty queue
        # The worker will keep looping on None, but no new jobs will be submitted.
        mock_client.brpop.side_effect = [
            (b'frontpunch:queue:default', job1_payload.encode('utf-8')),
            (b'frontpunch:queue:default', job2_payload.encode('utf-8')),
        ] + ([None] * 10) # Subsequent calls return None

        # Concurrency is 2, so both jobs should run at the same time
        worker = Worker(queues=['default'], concurrency=2, client=mock_client)

        # 2. Run worker in a separate, daemonic thread
        worker_thread = threading.Thread(target=worker.run, daemon=True)
        start_time = time.time()
        worker_thread.start()

        # 3. Wait for jobs to complete
        # Total time for sequential execution would be > 0.4s.
        # For concurrent, it should be > 0.2s. We'll wait for 0.3s.
        time.sleep(job_duration + 0.15)
        end_time = time.time()

        # 4. Assertions
        self.assertEqual(len(execution_times), 2, "Both jobs should have executed")

        # Total time should be less than the sum of job durations
        total_duration = end_time - start_time
        self.assertLess(total_duration, job_duration * 2, "Jobs should run in parallel, not series")
        self.assertGreater(total_duration, job_duration, "Execution should take at least one job's duration")

        # The start times of the two tasks should be very close
        time_diff = abs(execution_times[0] - execution_times[1])
        self.assertLess(time_diff, 0.1, "Jobs should start at almost the same time")

    def tearDown(self):
        # Re-enable logging after tests
        logging.disable(logging.NOTSET)

if __name__ == '__main__':
    unittest.main()
