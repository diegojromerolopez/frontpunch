import json
import logging
from importlib import import_module

try:
    from valkey import Valkey
except ImportError:
    Valkey = None

class Worker:
    """
    A simple worker that fetches jobs from Valkey queues and executes them.
    """
    def __init__(self, queues, concurrency=1, client=None, valkey_url="valkey://localhost:6379"):
        """
        Initializes the worker.

        :param queues: A list of queue names to listen to, in order of priority.
        :param concurrency: The number of concurrent jobs to run (not implemented yet).
        :param client: An existing Valkey client instance. If not provided, a new one is created.
        :param valkey_url: The Valkey URL to connect to if a client is not provided.
        """
        self.queues = queues
        self.concurrency = concurrency
        
        if client:
            self.client = client
        else:
            if Valkey is None:
                raise ImportError("Valkey client not provided and 'valkey' package not installed.")
            self.client = Valkey.from_url(valkey_url)
            
        self.queue_keys = [f"frontpunch:queue:{q}" for q in self.queues]

    def _fetch_job(self, timeout=1):
        """
        Fetches a job from the queues using a blocking pop (BRPOP).
        Returns a tuple (queue_name, job_data) or None if a timeout occurs.
        """
        return self.client.brpop(self.queue_keys, timeout=timeout)

    def process_job(self, job_data):
        """
        Deserializes and executes a job. Handles various error conditions.
        """
        try:
            # job_data is bytes, decode it first
            payload = json.loads(job_data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logging.error(f"Failed to decode JSON payload: {job_data!r}")
            return

        try:
            func_path = payload.get('func')
            if not func_path or not isinstance(func_path, str):
                 logging.error(f"Invalid or missing 'func' in payload: {payload}")
                 return

            module_path, func_name = func_path.rsplit('.', 1)
            module = import_module(module_path)
            func = getattr(module, func_name)
        except (ImportError, AttributeError, ValueError):
            logging.error(f"Failed to import function: {payload.get('func')}")
            return

        args = payload.get('args', [])
        
        try:
            if isinstance(args, list):
                func(*args)
            elif isinstance(args, dict):
                func(**args)
            else:
                logging.error(f"Invalid 'args' type in payload: {type(args)}")
        except Exception as e:
            # Catching a broad exception to prevent the worker from crashing.
            logging.error(f"Job execution failed for {payload.get('func')}: {e}", exc_info=True)

    def run(self, burst=False):
        """
        Main worker loop. Fetches and processes jobs continuously.
        
        :param burst: If True, the worker will exit after processing one job or timing out.
        """
        while True:
            job = self._fetch_job()
            if job:
                _queue_name, job_data = job
                self.process_job(job_data)
            
            if burst:
                break
