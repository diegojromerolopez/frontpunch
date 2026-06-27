import unittest
from click.testing import CliRunner

from frontpunch.cli import main

class TestCliWorkerE2E(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_worker_happy_path_default_concurrency(self):
        """
        E2E test for the worker command happy path with default concurrency.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'default,high_priority'])
        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        self.assertIsNone(result.exception)

    def test_worker_happy_path_explicit_concurrency(self):
        """
        E2E test for the worker command happy path with explicit positive concurrency.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'default', '--concurrency', '5'])
        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        self.assertIsNone(result.exception)
