import uuid
import json
import inspect
from datetime import datetime, timezone

def create_job_payload(func, *args, **kwargs):
    """
    Generates a JobPayload as a Python dictionary and serializes it to a JSON string.

    This function creates a job definition that can be sent to a Front-Punch worker.
    It captures the target function, its arguments, and adds metadata like a unique
    job ID and timestamps.

    Args:
        func (callable): The function to be executed by the worker.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        str: A JSON-serialized string representing the job payload.

    Raises:
        TypeError: If any of the provided `args` or `kwargs` are not
                   JSON-serializable.
        ValueError: If the function's module cannot be determined.
    """
    if not callable(func):
        raise TypeError("The 'func' argument must be a callable.")

    try:
        module = inspect.getmodule(func)
        if module is None or not hasattr(module, '__name__'):
            raise ValueError("Could not determine the module for the given function.")
        class_path = f"{module.__name__}.{func.__name__}"
    except (AttributeError, ValueError):
        raise ValueError(
            "The 'func' must be a function defined in a discoverable module, "
            "not a lambda or a dynamically generated function."
        )

    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "jid": job_id,
        "class": class_path,
        "args": args,
        "kwargs": kwargs,
        "created_at": created_at,
        "status": "queued",
    }

    try:
        serialized_payload = json.dumps(payload)
        return serialized_payload
    except TypeError as e:
        raise TypeError(f"Arguments for job '{class_path}' are not JSON-serializable: {e}")
