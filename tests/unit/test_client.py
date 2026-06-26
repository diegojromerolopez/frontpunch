import unittest
from unittest.mock import MagicMock

import redis

from frontpunch.client import Client, _get_queue_key
from frontpunch.connections import ConnectionManager
from frontpunch.exceptions import ConnectionError

class TestClient(unittest.TestCase):

    def setUp(self):
        self.mock_connection_manager = MagicMock(spec=ConnectionManager)
        self.mock_redis_conn = MagicMock(spec=redis.Redis)
        self.mock_connection_manager.get_connection.return_value = self.mock_redis_conn
        self.client = Client(self.mock_connection_manager)

    def test_get_queue_key(self):
        """Tests the queue key generation."""
        self.assertEqual(_get_queue_key("default"), "frontpunch:queue:default")
        self.assertEqual(_get_queue_key("high_priority"), "frontpunch:queue:high_priority")

    def test_enqueue_success(self):
        """Tests successful enqueueing of a job."""
        queue_name = "test_queue"
        payload = '{"job_id": "123", "data": "test"}'
        expected_key = f"frontpunch:queue:{queue_name}"

        self.client._enqueue(queue_name, payload)

        self.mock_connection_manager.get_connection.assert_called_once()
        self.mock_redis_conn.lpush.assert_called_once_with(expected_key, payload)

    def test_enqueue_lpush_connection_failure(self):
        """Tests that ConnectionError is raised on Redis lpush failure."""
        self.mock_redis_conn.lpush.side_effect = redis.exceptions.ConnectionError("Redis down")

        queue_name = "test_queue"
        payload = '{"job_id": "123", "data": "test"}'

        with self.assertRaises(ConnectionError) as cm:
            self.client._enqueue(queue_name, payload)

        self.assertIn("Failed to connect to Redis", str(cm.exception))
        self.mock_connection_manager.get_connection.assert_called_once()

    def test_get_connection_failure(self):
        """Tests that ConnectionError is raised if getting a connection fails."""
        self.mock_connection_manager.get_connection.side_effect = redis.exceptions.ConnectionError("Redis down")

        queue_name = "test_queue"
        payload = '{"job_id": "123", "data": "test"}'

        with self.assertRaises(ConnectionError):
            self.client._enqueue(queue_name, payload)

if __name__ == '__main__':
    unittest.main()
