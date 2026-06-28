class Worker:
    def __init__(self, redis_client, queues, tasks):
        self.redis_client = redis_client
        self.queues = queues
        self.tasks = tasks

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculates the delay for the next retry using exponential backoff.
        Formula: delay = 15 + (retry_count * 10) + (retry_count**4)
        """
        delay = 15 + (retry_count * 10) + (retry_count**4)
        return float(delay)
