import json
import time
import unittest
from unittest.mock import MagicMock, patch

from frontpunch.worker import Worker


class TestRetryBackoffFormula(unittest.TestCase):
    """
    Tests the exponential backoff formula in the Worker class.
    """

    def setUp(self):
        """
        Set up a Worker instance for testing.
        """
        # The _calculate_backoff_delay method is a pure function and doesn't use
        # any instance attributes, but we need to instantiate the class.
        mock_redis_client = MagicMock()
        self.worker = Worker(
            redis_client=mock_redis_client,
            queues=['default'],
            tasks={'test_task': MagicMock()}
        )

    def test_calculate_backoff_delay(self):
        """
        Validates the _calculate_backoff_delay function for specific retry counts.
        """
        # Formula: delay = 15 + (retry_count * 10) + (retry_count**4)

        # Test with retry_count = 0
        # Expected: 15 + (0 * 10) + (0**4) = 15
        self.assertEqual(self.worker._calculate_backoff_delay(0), 15.0)

        # Test with retry_count = 1
        # Expected: 15 + (1 * 10) + (1**4) = 26
        self.assertEqual(self.worker._calculate_backoff_delay(1), 26.0)

        # Test with retry_count = 2
        # Expected: 15 + (2 * 10) + (2**4) = 15 + 20 + 16 = 51
        self.assertEqual(self.worker._calculate_backoff_delay(2), 51.0)

        # Test with retry_count = 5
        # Expected: 15 + (5 * 10) + (5**4) = 15 + 50 + 625 = 690
        self.assertEqual(self.worker._calculate_backoff_delay(5), 690.0)


class TestWorkerExceptionHandling(unittest.TestCase):
    """
    Tests the worker's exception handling, retry, and dead-letter queue logic.
    """

    def setUp(self):
        """
        Set up a worker with a mock Redis client and a failing task.
        """
        self.mock_redis_client = MagicMock()
        self.mock_task = MagicMock()
        self.mock_task.side_effect = ValueError("Task failed!")
        self.worker = Worker(
            redis_client=self.mock_redis_client,
            queues=['default'],
            tasks={'failing_task': self.mock_task}
        )

    @patch('time.time', return_value=1000.0)
    def test_successful_retry(self, mock_time):
        """
        AC-1: Tests that a failed job is rescheduled for retry.
        """
        job_payload = {
            "task": "failing_task",
            "args": [1, 2],
            "max_retries": 3,
            "retry_count": 0
        }
        job_payload_str = json.dumps(job_payload)
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        with self.assertRaises(StopIteration):
            self.worker.run()

        self.mock_redis_client.zadd.assert_called_once()
        self.mock_redis_client.lpush.assert_not_called()

        # Verify the details of the zadd call
        args, kwargs = self.mock_redis_client.zadd.call_args
        self.assertEqual(args[0], "frontpunch:scheduled")

        # The payload is the key in the dict passed to zadd
        payload_str_sent = list(args[1].keys())[0]
        payload_sent = json.loads(payload_str_sent)

        self.assertEqual(payload_sent['retry_count'], 1)
        self.assertEqual(payload_sent['error_class'], 'ValueError')
        self.assertEqual(payload_sent['error_message'], 'Task failed!')
        # Ensure original payload is preserved
        self.assertEqual(payload_sent['task'], 'failing_task')
        self.assertEqual(payload_sent['max_retries'], 3)

        # Verify the score (scheduled time)
        score_sent = list(args[1].values())[0]
        expected_delay = self.worker._calculate_backoff_delay(1)  # retry_count is now 1
        expected_score = 1000.0 + expected_delay
        self.assertAlmostEqual(score_sent, expected_score)

    def test_exhausted_retries_moves_to_dead_letter_queue(self):
        """
        AC-2: Tests that a job with exhausted retries is moved to the dead-letter queue.
        """
        job_payload = {
            "task": "failing_task",
            "args": [],
            "max_retries": 3,
            "retry_count": 3  # retries exhausted
        }
        job_payload_str = json.dumps(job_payload)
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        with self.assertRaises(StopIteration):
            self.worker.run()

        self.mock_redis_client.zadd.assert_not_called()
        self.mock_redis_client.lpush.assert_called_once()

        args, kwargs = self.mock_redis_client.lpush.call_args
        self.assertEqual(args[0], "frontpunch:dead")

        payload_sent = json.loads(args[1])
        self.assertEqual(payload_sent['retry_count'], 3)
        self.assertEqual(payload_sent['error_class'], 'ValueError')
        self.assertEqual(payload_sent['error_message'], 'Task failed!')

    def test_max_retries_zero_moves_to_dead_letter_queue(self):
        """
        BR-1: Tests that a job with max_retries=0 goes directly to the dead-letter queue.
        """
        job_payload = {
            "task": "failing_task",
            "args": [],
            "max_retries": 0,  # retries disabled
            "retry_count": 0
        }
        job_payload_str = json.dumps(job_payload)
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        with self.assertRaises(StopIteration):
            self.worker.run()

        self.mock_redis_client.zadd.assert_not_called()
        self.mock_redis_client.lpush.assert_called_once()

        args, kwargs = self.mock_redis_client.lpush.call_args
        self.assertEqual(args[0], "frontpunch:dead")

        payload_sent = json.loads(args[1])
        self.assertEqual(payload_sent['retry_count'], 0)
        self.assertEqual(payload_sent['error_class'], 'ValueError')
        self.assertEqual(payload_sent['error_message'], 'Task failed!')
