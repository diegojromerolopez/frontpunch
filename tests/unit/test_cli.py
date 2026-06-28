import unittest
from unittest.mock import patch
from click.testing import CliRunner
from frontpunch.cli import main

class TestCliWorker(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch('frontpunch.cli.Worker')
    def test_worker_command_happy_path(self, MockWorker):
        """
        Test the worker command with valid arguments.
        """
        mock_worker_instance = MockWorker.return_value
        
        result = self.runner.invoke(main, ['worker', '--queues', 'q1,q2', '--concurrency', '5'])

        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        
        # Verify Worker was instantiated correctly
        MockWorker.assert_called_once_with(queues=['q1', 'q2'], concurrency=5)
        
        # Verify run() was called
        mock_worker_instance.run.assert_called_once()

        # Verify startup messages
        self.assertIn("Starting worker with concurrency 5...", result.output)
        self.assertIn("Listening on queues: q1, q2", result.output)

    @patch('frontpunch.cli.Worker')
    def test_worker_command_default_concurrency(self, MockWorker):
        """
        Test the worker command uses the default concurrency of 1.
        """
        mock_worker_instance = MockWorker.return_value
        
        result = self.runner.invoke(main, ['worker', '--queues', 'default_queue'])

        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        
        MockWorker.assert_called_once_with(queues=['default_queue'], concurrency=1)
        mock_worker_instance.run.assert_called_once()
        self.assertIn("Starting worker with concurrency 1...", result.output)
        self.assertIn("Listening on queues: default_queue", result.output)

    @patch('frontpunch.cli.Worker')
    def test_worker_command_queue_parsing(self, MockWorker):
        """
        Test that queue names are correctly parsed and stripped of whitespace.
        """
        result = self.runner.invoke(main, ['worker', '--queues', ' q1 , q2,q3 '])
        
        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        MockWorker.assert_called_once_with(queues=['q1', 'q2', 'q3'], concurrency=1)

    def test_worker_command_invalid_concurrency_zero(self):
        """
        Test the worker command fails with concurrency set to 0.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'q1', '--concurrency', '0'])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: Concurrency must be a positive integer.", result.output)

    def test_worker_command_invalid_concurrency_negative(self):
        """
        Test the worker command fails with negative concurrency.
        """
        result = self.runner.invoke(main, ['worker', '--queues', 'q1', '--concurrency', '-5'])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: Concurrency must be a positive integer.", result.output)

    def test_worker_command_missing_queues(self):
        """
        Test the worker command fails if --queues is not provided.
        """
        result = self.runner.invoke(main, ['worker'])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: Missing option '--queues'", result.output)

    @patch('frontpunch.cli.Worker')
    @patch('frontpunch.cli.logging')
    def test_worker_command_handles_import_error(self, mock_logging, MockWorker):
        """
        Test that a critical error is logged if the Worker fails to start due to ImportError.
        """
        MockWorker.side_effect = ImportError("Valkey not installed")
        mock_logger = mock_logging.getLogger.return_value

        result = self.runner.invoke(main, ['worker', '--queues', 'q1'])

        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        
        mock_logger.critical.assert_called_once_with("Could not start worker: Valkey not installed")

    @patch('frontpunch.cli.Worker')
    @patch('frontpunch.cli.logging')
    def test_worker_command_handles_generic_exception(self, mock_logging, MockWorker):
        """
        Test that a critical error is logged if the Worker fails to start due to a generic Exception.
        """
        mock_worker_instance = MockWorker.return_value
        mock_worker_instance.run.side_effect = Exception("Something went wrong")
        mock_logger = mock_logging.getLogger.return_value

        result = self.runner.invoke(main, ['worker', '--queues', 'q1'])

        self.assertEqual(result.exit_code, 0, msg=f"CLI command failed with output: {result.output}")
        
        mock_logger.critical.assert_called_once_with("Could not start worker: Something went wrong")
