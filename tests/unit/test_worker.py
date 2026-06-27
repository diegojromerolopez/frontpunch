import unittest
from unittest.mock import Mock, patch

# We might need to handle the case where Valkey is not installed
try:
    from valkey import Valkey
except ImportError:
    Valkey = None

from frontpunch.worker import Worker

class TestWorkerUnit(unittest.TestCase):
    def setUp(self):
        # Mock the Valkey client to avoid real network calls
        self.mock_client = Mock()
        # We can initialize the worker with the mock client
        self.worker = Worker(queues=['high', 'default'], concurrency=1, client=self.mock_client)

    def test_fetch_job_calls_brpop_with_correct_arguments(self):
        """
        Verify that _fetch_job calls brpop with correctly formatted queue keys and timeout.
        """
        self.worker._fetch_job()

        # Expected queue keys based on the worker's configuration
        expected_queue_keys = ['frontpunch:queue:high', 'frontpunch:queue:default']

        # Assert that brpop was called once with the correct arguments
        self.mock_client.brpop.assert_called_once_with(expected_queue_keys, timeout=1)

    def test_fetch_job_returns_job_data_on_success(self):
        """
        Verify that _fetch_job returns the data provided by brpop.
        """
        # Configure the mock to return a sample job tuple
        expected_job = (b'frontpunch:queue:high', b'{"job_id": "123"}')
        self.mock_client.brpop.return_value = expected_job

        # Call the method
        job = self.worker._fetch_job()

        # Assert that the returned job matches the mock's return value
        self.assertEqual(job, expected_job)

    def test_fetch_job_returns_none_on_timeout(self):
        """
        Verify that _fetch_job returns None when brpop times out.
        """
        # Configure the mock to return None, simulating a timeout
        self.mock_client.brpop.return_value = None

        # Call the method
        job = self.worker._fetch_job()

        # Assert that the method returns None
        self.assertIsNone(job)

    def test_init_without_client_and_valkey_installed(self):
        """
        Verify that Worker can be initialized without a client if Valkey is installed.
        This test relies on mocking Valkey.from_url.
        """
        if Valkey is None:
            self.skipTest("valkey package not installed")

        with patch('valkey.Valkey.from_url') as mock_from_url:
            mock_from_url.return_value = self.mock_client
            worker = Worker(queues=['test'], concurrency=1)
            self.assertIs(worker.client, self.mock_client)
            mock_from_url.assert_called_once_with("valkey://localhost:6379")

    def test_init_raises_importerror_if_no_client_and_no_valkey(self):
        """
        Verify that Worker raises ImportError if no client is provided and Valkey is not installed.
        """
        with patch('frontpunch.worker.Valkey', None):
            with self.assertRaises(ImportError) as cm:
                Worker(queues=['test'], concurrency=1)
            self.assertEqual(
                str(cm.exception),
                "Valkey client not provided and 'valkey' package not installed."
            )
