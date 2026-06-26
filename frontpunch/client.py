import json

class Client:
    _instance = None
    _jobs = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Client, cls).__new__(cls)
            # Ensure _jobs is initialized for the new instance
            cls._instance._jobs = {}
        return cls._instance

    def enqueue(self, job, queue_name):
        """In a real client, this would push the job to a broker like Redis."""
        if queue_name not in self._jobs:
            self._jobs[queue_name] = []
        self._jobs[queue_name].append(job)

    def get_jobs(self, queue_name):
        """Test helper to inspect jobs in the mock queue."""
        return self._jobs.get(queue_name, [])

    def clear_jobs(self):
        """Test helper to clear all mock queues."""
        self._jobs = {}
