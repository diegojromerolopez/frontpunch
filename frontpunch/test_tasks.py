import time
from typing import List, Optional, Any

# A global list to record execution times for testing concurrency.
# This is a simple mechanism for inter-thread/process communication in a test context.
GLOBAL_RECORD_LIST: List[float] = []

def recording_task(duration: float):
    """
    A simple task that records its start time and sleeps for a given duration.
    """
    GLOBAL_RECORD_LIST.append(time.time())
    time.sleep(duration)

def long_running_task(duration: float, started_event: Optional[Any] = None, finished_event: Optional[Any] = None):
    """
    A task that signals when it has started and when it has finished.
    Used for testing graceful shutdown. The events can be threading.Event,
    multiprocessing.Event, or any object with a .set() method.
    """
    if started_event:
        started_event.set()
    time.sleep(duration)
    if finished_event:
        finished_event.set()

def simple_task(*args, **kwargs):
    """A task that does nothing, for simple execution tests."""
    pass
