import json
import threading
import time
import unittest

import redis

from frontpunch import test_tasks
from frontpunch.worker import Worker

try:
    redis_client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
    redis_client.ping()
    IS_REDIS_AVAILABLE = True
except redis.exceptions.ConnectionError:
    IS_REDIS_AVAILABLE = False

@unittest.skipIf(not IS_REDIS_AVAILABLE, "Redis server not available")
class TestWorkerIntegration(unittest.TestCase):

    def setUp(self):
        self.redis_client = redis.Redis(host="localhost", port=6379, db=15)
        self.worker_queues = ["integration_test_queue"]
        self.scheduled_queue = "frontpunch:scheduled"
        self.dead_queue = "frontpunch:dead"
        
        self.redis_client.delete(*self.worker_queues, self.scheduled_queue, self.dead_queue)
        test_tasks.GLOBAL_RECORD_LIST.clear()
        test_tasks.FAIL_COUNTER.clear()

        self.tasks = {
            "failing_task": test_tasks.failing_task,
            "conditionally_failing_task": test_tasks.conditionally_failing_task,
        }
        worker_redis_client = redis.Redis(host="localhost", port=6379, db=15)
        self.worker = Worker(worker_redis_client, self.worker_queues, self.tasks)
        self.worker_thread = None

    def tearDown(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker.running = False
            try:
                self.redis_client.rpush(self.worker_queues[0], "{}")
            except Exception:
                pass # Ignore connection errors if redis is down
            self.worker_thread.join(timeout=2)
        self.redis_client.delete(*self.worker_queues, self.scheduled_queue, self.dead_queue)

    def _start_worker(self):
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()
        time.sleep(0.1)

    def test_job_fails_and_is_rescheduled_for_retry(self):
        self._start_worker()

        job_payload = {
            "task": "failing_task",
            "args": ["job1"],
            "max_retries": 3,
        }
        self.redis_client.rpush(self.worker_queues[0], json.dumps(job_payload))

        time.sleep(0.5)

        self.assertEqual(self.redis_client.llen(self.worker_queues[0]), 0)
        self.assertEqual(self.redis_client.zcard(self.scheduled_queue), 1)
        self.assertEqual(self.redis_client.llen(self.dead_queue), 0)

        scheduled_jobs = self.redis_client.zrange(self.scheduled_queue, 0, -1, withscores=True, score_cast_func=float)
        payload_str, score = scheduled_jobs[0]
        payload = json.loads(payload_str)

        self.assertGreater(score, time.time())
        self.assertEqual(payload["task"], "failing_task")
        self.assertEqual(payload["retry_count"], 1)
        self.assertEqual(payload["error_class"], "ValueError")
        self.assertIn("designed to fail", payload["error_message"])

    def test_job_fails_with_retries_disabled_goes_to_dead_queue(self):
        self._start_worker()

        job_payload = {
            "task": "failing_task",
            "args": ["job2"],
            "max_retries": 0,
        }
        self.redis_client.rpush(self.worker_queues[0], json.dumps(job_payload))

        time.sleep(0.5)

        self.assertEqual(self.redis_client.llen(self.worker_queues[0]), 0)
        self.assertEqual(self.redis_client.zcard(self.scheduled_queue), 0)
        self.assertEqual(self.redis_client.llen(self.dead_queue), 1)

        dead_job_str = self.redis_client.lpop(self.dead_queue)
        payload = json.loads(dead_job_str)

        self.assertEqual(payload["task"], "failing_task")
        self.assertEqual(payload.get("retry_count", 0), 0)
        self.assertEqual(payload["error_class"], "ValueError")

    def test_job_exhausts_retries_and_goes_to_dead_queue(self):
        self._start_worker()

        job_payload = {
            "task": "failing_task",
            "args": ["job3"],
            "max_retries": 1,
            "retry_count": 0,
        }
        self.redis_client.rpush(self.worker_queues[0], json.dumps(job_payload))
        time.sleep(0.5)

        self.assertEqual(self.redis_client.zcard(self.scheduled_queue), 1)
        self.assertEqual(self.redis_client.llen(self.dead_queue), 0)
        
        scheduled_jobs = self.redis_client.zrange(self.scheduled_queue, 0, -1)
        retried_payload_str = scheduled_jobs[0]
        retried_payload = json.loads(retried_payload_str)
        self.assertEqual(retried_payload["retry_count"], 1)

        self.redis_client.zrem(self.scheduled_queue, retried_payload_str)
        self.redis_client.rpush(self.worker_queues[0], retried_payload_str)
        time.sleep(0.5)

        self.assertEqual(self.redis_client.llen(self.worker_queues[0]), 0)
        self.assertEqual(self.redis_client.zcard(self.scheduled_queue), 0)
        self.assertEqual(self.redis_client.llen(self.dead_queue), 1)

        dead_job_str = self.redis_client.lpop(self.dead_queue)
        payload = json.loads(dead_job_str)
        self.assertEqual(payload["task"], "failing_task")
        self.assertEqual(payload["retry_count"], 1)
        self.assertEqual(payload["error_class"], "ValueError")
