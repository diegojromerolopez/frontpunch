import unittest
import time
import os

try:
    from valkey import Valkey
except ImportError:
    Valkey = None

from frontpunch.worker import Worker

# Skip integration tests if valkey is not installed or no test server is available
VALKEY_URL = os.environ.get("VALKEY_URL", "valkey://localhost:6379")
SKIP_TESTS = Valkey is None
try:
    if not SKIP_TESTS:
        Valkey.from_url(VALKEY_URL).ping()
except Exception:
    SKIP_TESTS = True

@unittest.skipIf(SKIP_TESTS, "Valkey package not installed or Valkey server not available")
class TestWorkerIntegration(unittest.TestCase):
    def setUp(self):
        """
        Set up a real Valkey client and clear the database before each test.
        """
        self.client = Valkey.from_url(VALKEY_URL)
        self.client.flushdb()

    def tearDown(self):
        """
        Clear the database after each test.
        """
        self.client.flushdb()

    def test_fetch_job_respects_queue_priority(self):
        """
        Verify that jobs are fetched from higher-priority queues first (BR-1).
        """
        # Worker is configured to check 'high' queue before 'low'
        worker = Worker(queues=['high', 'low'], concurrency=1, client=self.client)

        job_low = b'{"task": "low_priority"}'
        job_high = b'{"task": "high_priority"}'

        # Push jobs to the queues, low priority first
        self.client.lpush('frontpunch:queue:low', job_low)
        self.client.lpush('frontpunch:queue:high', job_high)

        # First fetch should get the job from the 'high' priority queue
        fetched_job_1 = worker._fetch_job()
        self.assertIsNotNone(fetched_job_1)
        self.assertEqual(fetched_job_1[0], b'frontpunch:queue:high')
        self.assertEqual(fetched_job_1[1], job_high)

        # Second fetch should get the job from the 'low' priority queue
        fetched_job_2 = worker._fetch_job()
        self.assertIsNotNone(fetched_job_2)
        self.assertEqual(fetched_job_2[0], b'frontpunch:queue:low')
        self.assertEqual(fetched_job_2[1], job_low)

        # No more jobs, should time out and return None
        fetched_job_3 = worker._fetch_job()
        self.assertIsNone(fetched_job_3)

    def test_fetch_job_blocks_and_timeouts(self):
        """
        Verify that _fetch_job blocks for approximately 1 second and returns None if no job is available.
        """
        worker = Worker(queues=['empty_queue'], concurrency=1, client=self.client)

        start_time = time.monotonic()
        result = worker._fetch_job()
        end_time = time.monotonic()

        duration = end_time - start_time

        # The result should be None as the queue is empty
        self.assertIsNone(result)

        # The duration should be close to the 1-second timeout.
        # We allow for a small margin of error.
        self.assertGreater(duration, 0.9)
        self.assertLess(duration, 1.2)

    def test_fetch_job_fetches_single_job(self):
        """
        A simple happy-path test to fetch a single job from a single queue.
        """
        worker = Worker(queues=['default'], concurrency=1, client=self.client)
        job_data = b'{"task": "some_task"}'

        # Push a job to the queue
        self.client.lpush('frontpunch:queue:default', job_data)

        # Fetch the job
        fetched_job = worker._fetch_job()

        # Verify the fetched job is correct
        self.assertIsNotNone(fetched_job)
        self.assertEqual(fetched_job[0], b'frontpunch:queue:default')
        self.assertEqual(fetched_job[1], job_data)

        # Verify the queue is now empty
        self.assertIsNone(self.client.lpop('frontpunch:queue:default'))
