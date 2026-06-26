import unittest
from unittest.mock import patch

from frontpunch import client as client_module
from frontpunch import enqueue
from frontpunch.jobs import Job
from .utils import TEST_QUEUE, mock_redis_client

def standalone_task(x, y):
    return x + y

class TestStandaloneEnqueue(unittest.TestCase):
    def setUp(self):
        self.redis_client = mock_redis_client()
        self.client = client_module.Frontpunch(redis_client=self.redis_client, queue_name=TEST_QUEUE)

        # Patch the get_default_client to return our test client
        self.get_client_patcher = patch('frontpunch.client.get_default_client')
        self.mock_get_client = self.get_client_patcher.start()
        self.mock_get_client.return_value = self.client

    def tearDown(self):
        self.get_client_patcher.stop()

    def test_enqueue_function(self):
        """Test that frontpunch.enqueue() enqueues a job."""
        job_id = enqueue(standalone_task, 1, 2)

        self.assertIsNotNone(job_id)
        self.redis_client.rpush.assert_called_once()
        args, _ = self.redis_client.rpush.call_args
        self.assertEqual(args[0], TEST_QUEUE)

        # Check the payload
        payload = args[1]
        job = Job.deserialize(payload)
        self.assertEqual(job.id, job_id)
        self.assertEqual(job.func_name, "tests.unit.test_enqueue.standalone_task")
        self.assertEqual(job.args, (1, 2))
        self.assertEqual(job.kwargs, {})

    def test_enqueue_with_kwargs(self):
        """Test frontpunch.enqueue() with keyword arguments."""
        job_id = enqueue(standalone_task, x=5, y=10)

        self.assertIsNotNone(job_id)
        self.redis_client.rpush.assert_called_once()
        args, _ = self.redis_client.rpush.call_args
        self.assertEqual(args[0], TEST_QUEUE)

        # Check the payload
        payload = args[1]
        job = Job.deserialize(payload)
        self.assertEqual(job.id, job_id)
        self.assertEqual(job.func_name, "tests.unit.test_enqueue.standalone_task")
        self.assertEqual(job.args, ())
        self.assertEqual(job.kwargs, {"x": 5, "y": 10})

if __name__ == '__main__':
    unittest.main()
