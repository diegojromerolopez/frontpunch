import unittest
from unittest.mock import MagicMock, patch, call
import logging

from frontpunch.worker import Worker

# Suppress logging for cleaner test output
logging.disable(logging.CRITICAL)

class TestWorkerRun(unittest.TestCase):

    def setUp(self):
        # Ensure logging is disabled for each test
        logging.disable(logging.CRITICAL)

    @patch('frontpunch.worker.ThreadPoolExecutor')
    def test_run_initializes_executor_and_submits_jobs(self, mock_executor_cls):
        """
        Verify that run() initializes ThreadPoolExecutor and submits fetched jobs.
        """
        # Setup
        mock_client = MagicMock()
        job_payload = b'{"path": "some.task", "args": {}}'
        worker = Worker(queues=['default'], concurrency=4, client=mock_client)

        mock_executor_instance = mock_executor_cls.return_value.__enter__.return_value

        # Use an exception to break the infinite loop in worker.run() for the test
        test_exception = StopIteration("Stopping test loop")
        worker._fetch_job = MagicMock(side_effect=[
            (b'queue:default', job_payload),
            test_exception
        ])

        # Run & Assert Exception
        with self.assertRaises(StopIteration) as cm:
            worker.run()
        self.assertIs(cm.exception, test_exception)

        # Assertions
        mock_executor_cls.assert_called_once_with(max_workers=4)
        # The mock is called twice: once to get the job, once to raise the exception
        self.assertEqual(worker._fetch_job.call_count, 2)
        mock_executor_instance.submit.assert_called_once_with(
            worker._execute_job,
            job_payload.decode('utf-8')
        )

    @patch('frontpunch.worker.ThreadPoolExecutor')
    def test_run_handles_no_job_fetched(self, mock_executor_cls):
        """
        Verify that run() does not submit a task when _fetch_job returns None.
        """
        # Setup
        mock_client = MagicMock()
        worker = Worker(queues=['default'], concurrency=2, client=mock_client)

        mock_executor_instance = mock_executor_cls.return_value.__enter__.return_value

        test_exception = StopIteration("Stopping test loop")
        worker._fetch_job = MagicMock(side_effect=[
            None,  # Simulate no job being available
            test_exception
        ])

        # Run & Assert Exception
        with self.assertRaises(StopIteration):
            worker.run()

        # Assertions
        mock_executor_cls.assert_called_once_with(max_workers=2)
        # The mock is called twice: once to get None, once to raise the exception
        self.assertEqual(worker._fetch_job.call_count, 2)
        mock_executor_instance.submit.assert_not_called()

    def tearDown(self):
        # Re-enable logging after tests
        logging.disable(logging.NOTSET)

if __name__ == '__main__':
    unittest.main()
