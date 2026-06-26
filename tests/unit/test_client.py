import unittest
from unittest.mock import patch, MagicMock
import json
import redis

from frontpunch.client import Frontpunch

# A simple function to be decorated for tests
def example_task(x, y):
    return x + y

class TestFrontpunchClientUnit(unittest.TestCase):
    """Unit tests for the Frontpunch client and job decorator."""

    @patch('redis.Redis')
    def test_decorator_returns_callable(self, mock_redis):
        """Test that the @fp.job decorator returns a callable object."""
        fp = Frontpunch(redis_client=mock_redis)
        decorated_task = fp.job(example_task)
        self.assertTrue(callable(decorated_task))

    @patch('redis.Redis')
    def test_payload_generation(self, mock_redis):
        """Test that the correct payload is generated and sent to Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        fp = Frontpunch()
        
        @fp.job
        def my_job(a, b, c=3):
            pass

        my_job(1, 'hello', c=4)

        # Check that lpush was called
        mock_redis_instance.lpush.assert_called_once()
        
        # Check the arguments of lpush
        call_args, call_kwargs = mock_redis_instance.lpush.call_args
        queue_name = call_args[0]
        payload_str = call_args[1]

        self.assertEqual(queue_name, 'frontpunch_queue')
        
        payload = json.loads(payload_str)
        self.assertEqual(payload['job'], 'my_job')
        self.assertEqual(payload['args'], [1, 'hello'])
        self.assertEqual(payload['kwargs'], {'c': 4})

    @patch('redis.Redis')
    def test_payload_generation_with_custom_queue(self, mock_redis):
        """Test payload generation with a custom queue name."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance

        fp = Frontpunch(queue_name='custom_tasks')

        @fp.job
        def another_task():
            pass

        another_task()

        mock_redis_instance.lpush.assert_called_once()
        call_args, _ = mock_redis_instance.lpush.call_args
        self.assertEqual(call_args[0], 'custom_tasks')

    @patch('redis.Redis')
    def test_non_serializable_args_raise_type_error(self, mock_redis):
        """Test that using non-JSON-serializable arguments raises a TypeError."""
        fp = Frontpunch(redis_client=mock_redis)

        @fp.job
        def failing_task(data):
            pass

        # A class instance is not JSON serializable by default
        class NonSerializable:
            pass

        with self.assertRaises(TypeError):
            failing_task(NonSerializable())


class TestFrontpunchClientIntegration(unittest.TestCase):
    """
    Integration-style tests for the Frontpunch client.
    These tests use a mocked Redis client to simulate interactions.
    """

    def setUp(self):
        """Set up a mock for redis.Redis for all tests in this class."""
        self.redis_patcher = patch('redis.Redis')
        self.mock_redis_class = self.redis_patcher.start()
        self.mock_redis_instance = MagicMock()
        self.mock_redis_class.return_value = self.mock_redis_instance

    def tearDown(self):
        """Stop the patcher."""
        self.redis_patcher.stop()

    def test_lpush_called_with_correct_arguments(self):
        """Verify that lpush is called with the correct queue and payload."""
        fp = Frontpunch(queue_name='integration_queue')

        @fp.job
        def integration_job(user_id, message):
            pass

        integration_job(123, "Welcome!")

        expected_payload = {
            "job": "integration_job",
            "args": [123, "Welcome!"],
            "kwargs": {}
        }
        expected_payload_str = json.dumps(expected_payload)

        self.mock_redis_instance.lpush.assert_called_once_with(
            'integration_queue',
            expected_payload_str
        )

    def test_connection_error_handling(self):
        """Test that Redis connection errors are handled gracefully."""
        # Configure the mock to raise a ConnectionError
        self.mock_redis_instance.lpush.side_effect = redis.exceptions.ConnectionError("Failed to connect")

        fp = Frontpunch()

        @fp.job
        def task_that_will_fail(a, b):
            pass

        # The decorator should propagate the exception
        with self.assertRaises(redis.exceptions.ConnectionError):
            task_that_will_fail(1, 2)

    def test_client_instantiation_with_mock_client(self):
        """Test that a pre-configured client can be passed."""
        mock_client = MagicMock()
        fp = Frontpunch(redis_client=mock_client)

        @fp.job
        def simple_job():
            pass
        
        simple_job()

        # Verify the provided client was used
        mock_client.lpush.assert_called_once()
        self.mock_redis_instance.lpush.assert_not_called() # The default one shouldn't be used
