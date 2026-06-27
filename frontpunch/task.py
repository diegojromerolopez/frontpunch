import functools
from .jobs import Job, serialize_job
from .redis_connector import RedisConnector

def task(queue, max_retries=0):
    """
    A decorator to register a function as a background task.

    Args:
        queue (str): The name of the queue to send jobs to.
        max_retries (int): The maximum number of times a job can be retried.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        def delay(*args, **kwargs):
            """
            Enqueues the task to be executed by a worker.
            """
            func_string = f"{func.__module__}.{func.__qualname__}"

            job = Job(
                func_string=func_string,
                args=args,
                kwargs=kwargs,
                max_retries=max_retries,
            )

            serialized_job = serialize_job(job)

            redis = RedisConnector.get_connection()
            queue_name = f"fp:queue:{queue}"
            redis.lpush(queue_name, serialized_job)

            return job.jid

        wrapper.delay = delay
        return wrapper

    return decorator
