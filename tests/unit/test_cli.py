import unittest
from click.testing import CliRunner
from click import UsageError

from frontpunch.cli import main

class TestCliWorkerValidation(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_worker_concurrency_zero(self):
        """
        Verify that a concurrency of 0 raises a UsageError.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'default', '--concurrency', '0'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, UsageError)
        self.assertEqual(str(result.exception), "Concurrency must be a positive integer.")

    def test_worker_concurrency_negative(self):
        """
        Verify that a negative concurrency raises a UsageError.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'default', '--concurrency', '-5'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, UsageError)
        self.assertEqual(str(result.exception), "Concurrency must be a positive integer.")

    def test_worker_concurrency_non_integer(self):
        """
        Verify that a non-integer concurrency raises a UsageError from click's type casting.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'default', '--concurrency', 'abc'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, UsageError)
        self.assertIn("Invalid value for '--concurrency': 'abc' is not a valid integer.", result.output)

    def test_worker_missing_queues(self):
        """
        Verify that missing the required --queues option raises a UsageError.
        """
        result = self.runner.invoke(main, ['worker'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsInstance(result.exception, UsageError)
        self.assertIn("Missing option '--queues'", result.output)
