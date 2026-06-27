import threading

# A list to record completed tasks
COMPLETED_TASKS = []
# Events for synchronization
TASK_STARTED = threading.Event()
FINISH_TASK = threading.Event()

def long_running_task(task_id):
    """
    A test task that signals when it has started and waits for a signal
    to finish. This allows tests to control its execution lifetime.
    """
    TASK_STARTED.set()  # Signal that the task has started
    FINISH_TASK.wait()  # Wait for the test to signal completion
    COMPLETED_TASKS.append(task_id)

def reset_task_events():
    """Resets the state for the next test."""
    COMPLETED_TASKS.clear()
    TASK_STARTED.clear()
    FINISH_TASK.clear()
