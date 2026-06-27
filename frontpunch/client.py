import json
import time
import uuid


class Client:
    """
    Frontpunch client to enqueue jobs.
    """
    def __init__(self, redis_client, queue_name="frontpunch"):
        """
        Initializes the client.

        Args:
            redis_client: An instance of a Redis client.
            queue_name (str): The name of the Redis list to use as a queue.
        """
        self.redis = redis_client
        self.queue_name = queue_name

    def push(self, worker_class, *args, **kwargs):
        """
        Creates a job payload and pushes it to the Redis queue.

        The job payload is a JSON string with the following schema:
        {
            "jid": "unique-job-id",
            "class": "WorkerClassName",
            "created_at": 1672531200.0,
            "args": [1, "foo"],
            "kwargs": {"bar": "baz"}
        }

        Args:
            worker_class (str): The name of the worker class to execute.
            *args: Positional arguments for the worker. Must be JSON-serializable.
            **kwargs: Keyword arguments for the worker. Must be JSON-serializable.

        Raises:
            TypeError: If args or kwargs contain non-JSON-serializable types.
        """
        job = {
            'jid': uuid.uuid4().hex,
            'class': worker_class,
            'created_at': time.time(),
            'args': args,
            'kwargs': kwargs,
        }
        # This will raise a TypeError if args or kwargs are not serializable,
        # which satisfies the test requirements.
        payload = json.dumps(job)
        self.redis.rpush(self.queue_name, payload)
