import click

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
