import unittest
from unittest.mock import patch, MagicMock
import logging

from frontpunch.worker import Worker

class TestWorker(unittest.TestCase):

    @patch('frontpunch.worker.Valkey')
    def test_worker_initialization_with_defaults(self, mock_valkey):
        """
        Test that the Worker initializes correctly with default client creation.
        """
        queues = ['default', 'high_priority']
        concurrency = 10

        mock_client_instance = MagicMock()
        mock_valkey.from_url.return_value = mock_client_instance

        worker = Worker(queues=queues, concurrency=concurrency)

        self.assertEqual(worker.queues, queues)
        self.assertEqual(worker.concurrency, concurrency)
        self.assertIsInstance(worker.logger, logging.Logger)
        self.assertEqual(worker.logger.name, 'frontpunch.worker')
        self.assertEqual(worker.logger.level, logging.INFO)
        
        # Check that a new client was created
        mock_valkey.from_url.assert_called_once_with("valkey://localhost:6379")
        self.assertIs(worker.client, mock_client_instance)

    @patch('frontpunch.worker.Valkey')
    def test_worker_initialization_with_provided_client(self, mock_valkey):
        """
        Test that the Worker uses a provided client instance.
        """
        queues = ['low_priority']
        concurrency = 5
        mock_client = MagicMock()

        worker = Worker(queues=queues, concurrency=concurrency, client=mock_client)

        self.assertEqual(worker.queues, queues)
        self.assertEqual(worker.concurrency, concurrency)
        self.assertIs(worker.client, mock_client)
        self.assertIsInstance(worker.logger, logging.Logger)
        self.assertEqual(worker.logger.name, 'frontpunch.worker')
        self.assertEqual(worker.logger.level, logging.INFO)

        # Check that a new client was NOT created
        mock_valkey.from_url.assert_not_called()

if __name__ == '__main__':
    unittest.main()
