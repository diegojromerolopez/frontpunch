import unittest
from unittest.mock import patch, MagicMock
import uuid

from frontpunch import task
from frontpunch.client import Client

# A sample function to be decorated, defined at the module level
def sample_task(x, y):
    """This is a sample task."""
    return x + y

class TestTaskDecorator(unittest.TestCase):

    def setUp(self):
        # Ensure a clean client state for each test
        Client().clear_jobs()

    def test_decorator_preserves_signature_br1(self):
        """BR-1: The decorator must wrap the target function, preserving its signature."""
        decorated_task = task(queue='default')(sample_task)
        self.assertEqual(decorated_task.__name__, 'sample_task')
        self.assertEqual(decorated_task.__doc__, 'This is a sample task.')

    def test_decorated_function_has_delay_method_fr2(self):
        """FR-2: It must attach a .delay(*args) method to the wrapped function."""
        decorated_task = task(queue='default')(sample_task)
        self.assertTrue(hasattr(decorated_task, 'delay'))
        self.assertTrue(callable(decorated_task.delay))

    @patch('frontpunch.tasks.Client')
    def test_delay_triggers_enqueue_and_returns_jid_fr2_ac1(self, MockClient):
        """FR-2, AC-1: Calling .delay() triggers enqueue logic and returns the jid."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.enqueue = MagicMock()

        # Use a predictable jid for the test
        test_jid = str(uuid.uuid4())

        with patch('uuid.uuid4', return_value=test_jid):
            decorated_task = task(queue='high_priority', max_retries=5)(sample_task)
            
            # Call .delay()
            returned_jid = decorated_task.delay(1, y=2)

            # AC-1: Check if jid is returned
            self.assertEqual(returned_jid, str(test_jid))

            # FR-2: Check if enqueue was called with the correct payload
            mock_client_instance.enqueue.assert_called_once()
            call_args, _ = mock_client_instance.enqueue.call_args
            
            expected_job_payload = {
                'jid': str(test_jid),
                'func': f'{sample_task.__module__}.{sample_task.__name__}',
                'args': (1,),
                'kwargs': {'y': 2},
                'queue': 'high_priority',
                'max_retries': 5,
                'retries': 0,
            }
            
            # The first argument to enqueue is the job dict
            self.assertEqual(call_args[0], expected_job_payload)
            # The second argument is the queue name
            self.assertEqual(call_args[1], 'high_priority')

    def test_calling_decorated_function_directly(self):
        """Test that the decorated function can still be called directly without enqueuing."""
        decorated_task = task(queue='default')(sample_task)
        result = decorated_task(5, 10)
        self.assertEqual(result, 15)
        # Verify no job was enqueued
        self.assertEqual(len(Client().get_jobs('default')), 0)

if __name__ == '__main__':
    unittest.main()
