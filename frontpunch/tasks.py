import functools
import uuid
from .client import Client

def task(queue, max_retries=3):
    """
    A decorator to register a function as a background task.

    Args:
        queue (str): The name of the queue to send the task to.
        max_retries (int): The maximum number of retries for the task.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Allow the function to be called directly
            return f(*args, **kwargs)

        def delay(*args, **kwargs):
            """
            Enqueues the task for background processing.

            Serializes the job and passes it to the client's enqueue method.
            Returns the job ID.
            """
            client = Client()
            job_id = str(uuid.uuid4())
            
            # Get the fully qualified function name
            func_path = f'{f.__module__}.{f.__name__}'

            job = {
                'jid': job_id,
                'func': func_path,
                'args': args,
                'kwargs': kwargs,
                'queue': queue,
                'max_retries': max_retries,
                'retries': 0,
            }
            client.enqueue(job, queue)
            return job_id

        wrapper.delay = delay
        return wrapper
    return decorator
