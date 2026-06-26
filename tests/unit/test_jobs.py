import unittest
import json
import uuid
from datetime import datetime

# A dummy function for testing purposes, defined at the module level
def sample_task(x, y):
    return x + y

class NonSerializable:
    """A simple class that is not JSON serializable by default."""
    pass

class TestJobPayloadSerialization(unittest.TestCase):

    def setUp(self):
        from frontpunch.jobs import create_job_payload
        self.create_job_payload = create_job_payload

    def test_successful_serialization(self):
        """
        Tests that a valid job payload is created and serialized correctly.
        """
        args = (1, 2)
        kwargs = {"z": 3}
        
        payload_str = self.create_job_payload(sample_task, *args, **kwargs)
        
        self.assertIsInstance(payload_str, str)
        
        payload_dict = json.loads(payload_str)
        
        self.assertIn("jid", payload_dict)
        self.assertIsInstance(payload_dict["jid"], str)
        try:
            uuid.UUID(payload_dict["jid"])
        except ValueError:
            self.fail("jid is not a valid UUID")
            
        self.assertEqual(payload_dict["class"], "tests.unit.test_jobs.sample_task")
        
        self.assertEqual(payload_dict["args"], list(args))
        self.assertEqual(payload_dict["kwargs"], kwargs)
        
        self.assertIn("created_at", payload_dict)
        try:
            # fromisoformat() in 3.11+ handles 'Z' suffix, older versions don't
            dt_str = payload_dict["created_at"].replace('Z', '+00:00')
            datetime.fromisoformat(dt_str)
        except ValueError:
            self.fail("created_at is not a valid ISO 8601 timestamp")

        self.assertEqual(payload_dict["status"], "queued")

    def test_non_serializable_arg_raises_type_error(self):
        """
        Tests that a TypeError is raised for non-serializable arguments.
        """
        non_serializable_obj = NonSerializable()
        
        with self.assertRaises(TypeError) as cm:
            self.create_job_payload(sample_task, non_serializable_obj)
            
        self.assertIn("not JSON-serializable", str(cm.exception))

    def test_non_serializable_kwarg_raises_type_error(self):
        """
        Tests that a TypeError is raised for non-serializable keyword arguments.
        """
        non_serializable_obj = set([1, 2, 3]) # Sets are not JSON serializable
        
        with self.assertRaises(TypeError) as cm:
            self.create_job_payload(sample_task, x=1, y=non_serializable_obj)
            
        self.assertIn("not JSON-serializable", str(cm.exception))

    def test_non_callable_func_raises_type_error(self):
        """
        Tests that a TypeError is raised if the 'func' argument is not callable.
        """
        with self.assertRaises(TypeError):
            self.create_job_payload(123, 1, 2)

    def test_lambda_func_raises_value_error(self):
        """
        Tests that a ValueError is raised for functions that don't have a clear module path.
        """
        with self.assertRaises(ValueError):
            self.create_job_payload(lambda x: x + 1, 1)

if __name__ == '__main__':
    unittest.main()
