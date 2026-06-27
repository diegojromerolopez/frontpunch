import unittest
from unittest.mock import Mock, patch
from frontpunch.worker import Worker

class TestWorkerShutdown(unittest.TestCase):
    def test_handle_shutdown(self):
        """
        Tests that _handle_shutdown sets the shutdown flag and logs a message.
        """
        # We don't need a real client for this unit test.
        mock_client = Mock()
        worker = Worker(queues=["test"], concurrency=1, client=mock_client)

        self.assertFalse(worker._shutdown)

        with patch.object(worker, 'logger') as mock_logger:
            # Simulate a signal call
            worker._handle_shutdown(None, None)

            self.assertTrue(worker._shutdown)
            mock_logger.info.assert_called_once_with(
                "Shutdown signal received. Stopping worker gracefully..."
            )

if __name__ == '__main__':
    unittest.main()
