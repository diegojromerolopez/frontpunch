import click
import logging
from .worker import Worker

@click.group()
def main():
    """Frontpunch CLI."""
    pass

@main.command()
@click.option('--queues', required=True, help='Comma-separated list of queues to process.')
@click.option('--concurrency', type=int, default=1, help='Number of concurrent workers.')
def worker(queues, concurrency):
    """
    Starts a Frontpunch worker.
    """
    if concurrency <= 0:
        raise click.UsageError("Concurrency must be a positive integer.")

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    queue_list = [q.strip() for q in queues.split(',')]
    
    # Using click.echo for direct user feedback on the console
    click.echo(f"Starting worker with concurrency {concurrency}...")
    click.echo(f"Listening on queues: {', '.join(queue_list)}")

    try:
        worker_instance = Worker(queues=queue_list, concurrency=concurrency)
        worker_instance.run()
    except (ImportError, Exception) as e:
        # This broad exception handling is per the spec for test environments
        # where Valkey might not be installed or running.
        logging.getLogger(__name__).critical(f"Could not start worker: {e}")
