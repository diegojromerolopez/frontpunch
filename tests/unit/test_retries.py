import unittest
from unittest.mock import MagicMock

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
