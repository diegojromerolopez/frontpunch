import json
import time
import unittest
from unittest.mock import MagicMock, patch, call

from frontpunch.worker import Worker

class TestWorkerExceptionHandling(unittest.TestCase):

    def setUp(self):
        self.mock_redis = MagicMock()
        self.mock_tasks = {
            "failing_task": MagicMock(side_effect=ValueError("Task failed")),
            "base_exception_task": MagicMock(side_effect=KeyboardInterrupt("Stop it")),
        }
        self.worker = Worker(self.mock_redis, ["test_queue"], self.mock_tasks)

    def test_calculate_backoff_delay(self):
        # Test with a few values to ensure the formula is correct
        self.assertEqual(self.worker._calculate_backoff_delay(0), 15.0)
        self.assertEqual(self.worker._calculate_backoff_delay(1), 26.0)
        self.assertEqual(self.worker._calculate_backoff_delay(2), 51.0)
        self.assertEqual(self.worker._calculate_backoff_delay(3), 126.0)

    @patch("frontpunch.worker.time.time")
    def test_job_fails_and_is_retried(self, mock_time):
        mock_time.return_value = 1000.0
        job_payload = {
            "task": "failing_task",
            "args": [1, 2],
            "max_retries": 3,
            "retry_count": 0,
        }
        job_payload_str = json.dumps(job_payload)

        # Simulate one job, then stop the worker
        self.mock_redis.blpop.side_effect = [
            ("test_queue", job_payload_str),
            KeyboardInterrupt("Stop worker"),
        ]

        with self.assertRaises(KeyboardInterrupt):
            self.worker.run()

        self.mock_tasks["failing_task"].assert_called_once_with(1, 2)

        expected_delay = self.worker._calculate_backoff_delay(1)
        expected_scheduled_time = 1000.0 + expected_delay

        self.mock_redis.zadd.assert_called_once()
        args, kwargs = self.mock_redis.zadd.call_args
        self.assertEqual(args[0], "frontpunch:scheduled")
        
        payload_map = args[1]
        self.assertEqual(len(payload_map), 1)
        
        rescheduled_payload_str = list(payload_map.keys())[0]
        rescheduled_score = list(payload_map.values())[0]
        rescheduled_payload = json.loads(rescheduled_payload_str)

        self.assertEqual(rescheduled_payload["retry_count"], 1)
        self.assertEqual(rescheduled_payload["error_class"], "ValueError")
        self.assertEqual(rescheduled_payload["error_message"], "Task failed")
        self.assertEqual(rescheduled_score, expected_scheduled_time)

        self.mock_redis.rpush.assert_not_called()

    def test_job_fails_and_exhausts_retries(self):
        job_payload = {
            "task": "failing_task",
            "args": [],
            "max_retries": 1,
            "retry_count": 1,
        }
        job_payload_str = json.dumps(job_payload)

        self.mock_redis.blpop.side_effect = [
            ("test_queue", job_payload_str),
            KeyboardInterrupt("Stop worker"),
        ]

        with self.assertRaises(KeyboardInterrupt):
            self.worker.run()

        self.mock_tasks["failing_task"].assert_called_once_with()

        self.mock_redis.rpush.assert_called_once()
        args, _ = self.mock_redis.rpush.call_args
        self.assertEqual(args[0], "frontpunch:dead")
        
        dead_payload = json.loads(args[1])
        self.assertEqual(dead_payload["retry_count"], 1)
        self.assertEqual(dead_payload["error_class"], "ValueError")
        self.assertEqual(dead_payload["error_message"], "Task failed")

        self.mock_redis.zadd.assert_not_called()

    def test_job_fails_with_retries_disabled(self):
        job_payload = {
            "task": "failing_task",
            "args": [],
            "max_retries": 0,
        }
        job_payload_str = json.dumps(job_payload)

        self.mock_redis.blpop.side_effect = [
            ("test_queue", job_payload_str),
            KeyboardInterrupt("Stop worker"),
        ]

        with self.assertRaises(KeyboardInterrupt):
            self.worker.run()

        self.mock_tasks["failing_task"].assert_called_once_with()

        self.mock_redis.rpush.assert_called_once()
        args, _ = self.mock_redis.rpush.call_args
        self.assertEqual(args[0], "frontpunch:dead")
        
        dead_payload = json.loads(args[1])
        self.assertEqual(dead_payload.get("retry_count", 0), 0)
        self.assertEqual(dead_payload["error_class"], "ValueError")
        self.assertEqual(dead_payload["error_message"], "Task failed")

        self.mock_redis.zadd.assert_not_called()

    def test_base_exception_is_not_caught(self):
        job_payload = {"task": "base_exception_task"}
        job_payload_str = json.dumps(job_payload)

        self.mock_redis.blpop.return_value = ("test_queue", job_payload_str)

        with self.assertRaises(KeyboardInterrupt):
            self.worker.run()

        self.mock_tasks["base_exception_task"].assert_called_once_with()

        self.mock_redis.zadd.assert_not_called()
        self.mock_redis.rpush.assert_not_called()
