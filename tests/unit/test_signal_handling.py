import unittest
from unittest.mock import MagicMock, patch
import signal
import os

from frontpunch.worker import Worker

class TestSignalHandling(unittest.TestCase):
    @patch('frontpunch.worker.signal')
    def test_register_signals(self, mock_signal):
        worker = Worker(MagicMock(), ["queue"], {})
        worker._register_signals()
        mock_signal.signal.assert_any_call(mock_signal.SIGTERM, worker._signal_handler)
        mock_signal.signal.assert_any_call(mock_signal.SIGINT, worker._signal_handler)

    @patch('frontpunch.worker.os._exit')
    def test_signal_handler_first_and_second_signals(self, mock_exit):
        worker = Worker(MagicMock(), ["queue"], {})
        worker.running = True
        
        # First signal
        worker._signal_handler(None, None)
        self.assertTrue(worker.shutdown_event.is_set())
        self.assertFalse(worker.running)
        mock_exit.assert_not_called()
        
        # Second signal
        worker._signal_handler(None, None)
        mock_exit.assert_called_once_with(1)

    @patch('frontpunch.worker.signal')
    def test_run_registers_signals(self, mock_signal):
        mock_redis = MagicMock()
        mock_redis.blpop.side_effect = KeyboardInterrupt("Stop")
        worker = Worker(mock_redis, ["queue"], {})
        try:
            worker.run()
        except KeyboardInterrupt:
            pass
        mock_signal.signal.assert_any_call(mock_signal.SIGTERM, worker._signal_handler)
        mock_signal.signal.assert_any_call(mock_signal.SIGINT, worker._signal_handler)
