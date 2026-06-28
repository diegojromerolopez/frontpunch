# This file is for test tasks used in integration tests.
# It's placed inside the package to avoid Python's double-import issues.

import time

# A list to record results from tasks, for assertion in tests.
# Not perfectly thread-safe but sufficient for these tests.
GLOBAL_RECORD_LIST = []

# A dictionary to track failure counts for tasks.
FAIL_COUNTER = {}

def recording_task(*args, **kwargs):
    """A simple task that records its arguments."""
    GLOBAL_RECORD_LIST.append({"args": args, "kwargs": kwargs, "timestamp": time.time()})

def failing_task(*args, **kwargs):
    """A task that is designed to always fail."""
    raise ValueError("This task is designed to fail")

def conditionally_failing_task(job_id, fail_times):
    """
    Fails `fail_times` times, then succeeds.
    Uses a global dictionary to track failures for a given job_id.
    """
    if job_id not in FAIL_COUNTER:
        FAIL_COUNTER[job_id] = 0

    current_attempt = FAIL_COUNTER.get(job_id, 0)

    if current_attempt < fail_times:
        FAIL_COUNTER[job_id] = current_attempt + 1
        raise RuntimeError(f"Failing on attempt {FAIL_COUNTER[job_id]}")
    else:
        # On success, record the successful execution
        GLOBAL_RECORD_LIST.append({"job_id": job_id, "status": "success"})
