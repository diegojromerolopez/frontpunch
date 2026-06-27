import time

# This list is intended to be patched by tests to observe side effects.
GLOBAL_RECORD_LIST = []

def simple_task(x, y):
    """A simple task for testing."""
    return x + y

def error_task():
    """A task that always raises an error."""
    raise ValueError("This is a test error")

def recording_task(duration):
    """
    Records the time of execution and sleeps for a given duration.
    Appends the start time to a global list that can be inspected in tests.
    """
    GLOBAL_RECORD_LIST.append(time.time())
    time.sleep(duration)
