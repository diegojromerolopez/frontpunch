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
        AC-1: A failing job with retries left is rescheduled with an updated payload.
        """
        # Arrange
        job_payload = {
            "task": "failing_task",
            "args": [1, 2],
            "retry_count": 0,
            "max_retries": 3
        }
        job_payload_str = json.dumps(job_payload)
        # Simulate blpop returning this job, then raise StopIteration to stop the worker loop
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        # Act
        with self.assertRaises(StopIteration):
            self.worker.run()

        # Assert
        # 1. Task was called
        self.mock_task.assert_called_once_with(1, 2)

        # 2. zadd was called to reschedule the job
        self.mock_redis_client.zadd.assert_called_once()
        self.mock_redis_client.rpush.assert_not_called()  # Should not go to DLQ

        # 3. Verify the zadd arguments
        zadd_args = self.mock_redis_client.zadd.call_args
        self.assertEqual(zadd_args.args[0], "frontpunch:scheduled")  # key

        # 4. Verify the updated payload and score
        payload_and_score = zadd_args.args[1]
        self.assertEqual(len(payload_and_score), 1)

        rescheduled_payload_str = list(payload_and_score.keys())[0]
        rescheduled_payload = json.loads(rescheduled_payload_str)
        score = list(payload_and_score.values())[0]

        self.assertEqual(rescheduled_payload['retry_count'], 1)
        self.assertEqual(rescheduled_payload['max_retries'], 3)
        self.assertEqual(rescheduled_payload['error_class'], 'ValueError')
        self.assertEqual(rescheduled_payload['error_message'], 'Task failed!')
        self.assertEqual(rescheduled_payload['task'], 'failing_task')
        self.assertEqual(rescheduled_payload['args'], [1, 2])

        # 5. Verify the score calculation
        # delay = 15 + (1 * 10) + (1**4) = 26
        expected_delay = self.worker._calculate_backoff_delay(1)
        self.assertEqual(expected_delay, 26.0)
        expected_score = 1000.0 + expected_delay
        self.assertEqual(score, expected_score)

    def test_exhausted_retries(self):
        """
        AC-2: A failing job with no retries left is sent to the dead-letter queue.
        """
        # Arrange
        job_payload = {
            "task": "failing_task",
            "args": [],
            "retry_count": 5,
            "max_retries": 5
        }
        job_payload_str = json.dumps(job_payload)
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        # Act
        with self.assertRaises(StopIteration):
            self.worker.run()

        # Assert
        # 1. Task was called
        self.mock_task.assert_called_once_with()

        # 2. rpush was called to send to DLQ
        self.mock_redis_client.rpush.assert_called_once()
        self.mock_redis_client.zadd.assert_not_called()  # Should not be rescheduled

        # 3. Verify rpush arguments
        rpush_args = self.mock_redis_client.rpush.call_args
        self.assertEqual(rpush_args.args[0], "frontpunch:dead")

        # 4. Verify the final payload
        final_payload_str = rpush_args.args[1]
        final_payload = json.loads(final_payload_str)

        self.assertEqual(final_payload['retry_count'], 5)  # Unchanged
        self.assertEqual(final_payload['max_retries'], 5)
        self.assertEqual(final_payload['error_class'], 'ValueError')
        self.assertEqual(final_payload['error_message'], 'Task failed!')
        self.assertEqual(final_payload['task'], 'failing_task')

    def test_max_retries_zero(self):
        """
        BR-1: A failing job with max_retries=0 is sent directly to the dead-letter queue.
        """
        # Arrange
        job_payload = {
            "task": "failing_task",
            "args": {"kwarg": "value"},
            "max_retries": 0  # This is the key part of the test
        }
        job_payload_str = json.dumps(job_payload)
        self.mock_redis_client.blpop.side_effect = [
            ('default', job_payload_str),
            StopIteration
        ]

        # Act
        with self.assertRaises(StopIteration):
            self.worker.run()

        # Assert
        # 1. Task was called
        self.mock_task.assert_called_once_with(kwarg="value")

        # 2. rpush was called to send to DLQ
        self.mock_redis_client.rpush.assert_called_once()
        self.mock_redis_client.zadd.assert_not_called()

        # 3. Verify rpush arguments
        rpush_args = self.mock_redis_client.rpush.call_args
        self.assertEqual(rpush_args.args[0], "frontpunch:dead")

        # 4. Verify the final payload
        final_payload_str = rpush_args.args[1]
        final_payload = json.loads(final_payload_str)

        # retry_count is not in the original payload, so it defaults to 0
        self.assertEqual(final_payload.get('retry_count', 0), 0)
        self.assertEqual(final_payload['max_retries'], 0)
        self.assertEqual(final_payload['error_class'], 'ValueError')
        self.assertEqual(final_payload['error_message'], 'Task failed!')
        self.assertEqual(final_payload['task'], 'failing_task')
        self.assertEqual(final_payload['args'], {"kwarg": "value"})
