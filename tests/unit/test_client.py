import unittest
from unittest.mock import patch, MagicMock

from frontpunch import client

class TestClientConfiguration(unittest.TestCase):

    def tearDown(self):
        # Reset the client state after each test
        client._reset_client()

    def test_get_client_before_configuration(self):
        """
        Test that get_client raises ConfigurationError if called before configure.
        """
        with self.assertRaises(client.ConfigurationError):
            client.get_client()

    @patch('redis.from_url')
    def test_configure_initializes_client(self, mock_from_url):
        """
        Test that configure initializes the Redis client with the given URL.
        """
        mock_redis_instance = MagicMock()
        mock_from_url.return_value = mock_redis_instance
        
        redis_url = "redis://localhost:6379/0"
        client.configure(redis_url=redis_url)
        
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)
        
        retrieved_client = client.get_client()
        self.assertIs(retrieved_client, mock_redis_instance)

    @patch('redis.from_url')
    def test_configure_multiple_times(self, mock_from_url):
        """
        Test that calling configure multiple times re-initializes the client.
        """
        mock_redis_instance1 = MagicMock()
        mock_redis_instance2 = MagicMock()
        mock_from_url.side_effect = [mock_redis_instance1, mock_redis_instance2]

        # First call
        redis_url1 = "redis://localhost:6379/1"
        client.configure(redis_url=redis_url1)
        retrieved_client1 = client.get_client()
        self.assertIs(retrieved_client1, mock_redis_instance1)
        mock_from_url.assert_called_with(redis_url1, decode_responses=True)
        self.assertEqual(mock_from_url.call_count, 1)

        # Second call
        redis_url2 = "redis://localhost:6379/2"
        client.configure(redis_url=redis_url2)
        retrieved_client2 = client.get_client()
        self.assertIs(retrieved_client2, mock_redis_instance2)
        mock_from_url.assert_called_with(redis_url2, decode_responses=True)
        self.assertEqual(mock_from_url.call_count, 2)

    def test_configuration_error_message(self):
        """
        Test the error message of ConfigurationError.
        """
        with self.assertRaisesRegex(client.ConfigurationError, "Frontpunch not configured. Please call frontpunch.configure() first."):
            client.get_client()

if __name__ == '__main__':
    unittest.main()
