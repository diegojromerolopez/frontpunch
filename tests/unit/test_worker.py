import unittest
from unittest.mock import MagicMock, patch, call
import threading
import signal
import logging

from frontpunch.worker import Worker

class TestWorkerShutdown(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock()

    def test_handle_shutdown_sets_event_and_logs(self):
        worker = Worker(queues=['test'], concurrency=1, client=self.mock_client)
        worker.logger.propagate = False
        self.assertFalse(worker.shutdown_event.is_set())

        with self.assertLogs(worker.logger, level='INFO') as cm:
            # We can use any signal number for the test
            worker._handle_shutdown(signal.SIGINT, None)
            self.assertTrue(worker.shutdown_event.is_set())
            
            log_output = cm.output[0]
            self.assertIn("Shutdown signal received", log_output)
            self.assertIn(f"(SIG {signal.SIGINT})", log_output)
            self.assertIn("Stopping job fetching...", log_output)

    @patch('frontpunch.worker.signal')
    @patch('frontpunch.worker.ThreadPoolExecutor')
    def test_run_registers_signals_in_main_thread(self, mock_executor, mock_signal):
        class StopTest(BaseException): pass

        with patch('frontpunch.worker.threading.current_thread', return_value=threading.main_thread()):
            worker = Worker(queues=['test'], concurrency=1, client=self.mock_client)
            worker._fetch_job = MagicMock(side_effect=StopTest)

            with self.assertRaises(StopTest):
                worker.run()

            expected_calls = [
                call(mock_signal.SIGINT, worker._handle_shutdown),
                call(mock_signal.SIGTERM, worker._handle_shutdown),
            ]
            mock_signal.signal.assert_has_calls(expected_calls, any_order=True)

    @patch('frontpunch.worker.signal')
    @patch('frontpunch.worker.ThreadPoolExecutor')
    def test_run_does_not_register_signals_in_worker_thread(self, mock_executor, mock_signal):
        class StopTest(BaseException): pass

        dummy_thread = threading.Thread()
        with patch('frontpunch.worker.threading.current_thread', return_value=dummy_thread):
            worker = Worker(queues=['test'], concurrency=1, client=self.mock_client)
            worker._fetch_job = MagicMock(side_effect=StopTest)

            with self.assertRaises(StopTest):
                worker.run()

            mock_signal.signal.assert_not_called()

    def test_fetch_job_returns_none_on_shutdown(self):
        worker = Worker(queues=['test'], concurrency=1, client=self.mock_client)
        worker.shutdown_event.set()

        result = worker._fetch_job()

        self.assertIsNone(result)
        self.mock_client.brpop.assert_not_called()
