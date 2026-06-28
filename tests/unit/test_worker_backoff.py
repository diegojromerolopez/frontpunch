import unittest
from unittest.mock import MagicMock

from frontpunch.worker import Worker


class TestWorkerBackoffDelay(unittest.TestCase):
    """
    Tests for the private _calculate_backoff_delay method in the Worker class.
    """

    def setUp(self):
        """
        Set up a Worker instance with mocked dependencies to test its methods.
        """
        # The Worker needs a redis_client, queues, and tasks for instantiation.
        # We can provide mocks for these as they are not used by the
        # _calculate_backoff_delay method.
        mock_redis_client = MagicMock()
        self.worker = Worker(
            redis_client=mock_redis_client,
            queues=['default'],
            tasks={'test_task': MagicMock()}
        )

    def test_calculate_backoff_delay_with_zero_retries(self):
        """
        Verify the backoff calculation for the initial attempt (0 retries).
        Formula: 15 + (0 * 10) + (0**4) = 15
        """
        self.assertEqual(self.worker._calculate_backoff_delay(0), 15.0)

    def test_calculate_backoff_delay_with_one_retry(self):
        """
        Verify the backoff calculation for the first retry.
        Formula: 15 + (1 * 10) + (1**4) = 26
        """
        self.assertEqual(self.worker._calculate_backoff_delay(1), 26.0)

    def test_calculate_backoff_delay_with_multiple_retries(self):
        """
        Verify the backoff calculation for subsequent retries.
        """
        # Test with retry_count = 2
        # Formula: 15 + (2 * 10) + (2**4) = 15 + 20 + 16 = 51
        self.assertEqual(self.worker._calculate_backoff_delay(2), 51.0)

        # Test with retry_count = 10
        # Formula: 15 + (10 * 10) + (10**4) = 15 + 100 + 10000 = 10115
        self.assertEqual(self.worker._calculate_backoff_delay(10), 10115.0)

    def test_calculate_backoff_delay_return_type(self):
        """
        Verify that the function returns a float.
        """
        delay = self.worker._calculate_backoff_delay(0)
        self.assertIsInstance(delay, float)
