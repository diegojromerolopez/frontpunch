import unittest
from unittest.mock import patch, MagicMock

try:
    import redis
    from frontpunch.client import RedisConnectionManager
except ImportError:
    redis = None
    RedisConnectionManager = None


@unittest.skipIf(RedisConnectionManager is None, "redis-py is not installed or frontpunch.client is missing")
class TestRedisConnectionManager(unittest.TestCase):

    @patch('redis.ConnectionPool.from_url')
    def test_initialization_with_redis_url(self, mock_from_url):
        """Test that the manager initializes a connection pool from a redis:// URL."""
        redis_url = "redis://localhost:6379/0"
        manager = RedisConnectionManager(redis_url)
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)
        self.assertIsNotNone(manager._pool)

    @patch('redis.ConnectionPool.from_url')
    def test_initialization_with_rediss_url(self, mock_from_url):
        """Test that the manager initializes a connection pool from a rediss:// URL."""
        redis_url = "rediss://user:password@my-secure-redis:6379/1"
        manager = RedisConnectionManager(redis_url)
        mock_from_url.assert_called_once_with(redis_url, decode_responses=True)
        self.assertIsNotNone(manager._pool)

    def test_initialization_with_empty_url(self):
        """Test that initialization fails with an empty URL."""
        with self.assertRaises(ValueError) as cm:
            RedisConnectionManager("")
        self.assertEqual(str(cm.exception), "redis_url cannot be empty.")

    @patch('redis.ConnectionPool.from_url')
    @patch('redis.Redis')
    def test_get_connection(self, mock_redis_class, mock_from_url):
        """Test that get_connection returns a client from the pool."""
        mock_pool = MagicMock()
        mock_from_url.return_value = mock_pool
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        redis_url = "redis://localhost:6379/0"
        manager = RedisConnectionManager(redis_url)
        
        connection = manager.get_connection()

        mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
        self.assertIs(connection, mock_redis_instance)

if __name__ == '__main__':
    unittest.main()
