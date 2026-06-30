import unittest
from unittest.mock import MagicMock, patch
import threading
import time

from frontpunch.worker import Worker

class TestSignalHandlingIntegration(unittest.TestCase):
    def test_graceful_shutdown_on_signal_integration(self):
        unblock_event = threading.Event()
        mock_redis = MagicMock()
        
        def blpop_side_effect(*args, **kwargs):
            unblock_event.wait(timeout=2.0)
            return None
            
        mock_redis.blpop.side_effect = blpop_side_effect
        
        worker = Worker(mock_redis, ["test_queue"], {})
        
        # Start worker in a separate thread
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()
        
        # Wait a tiny bit to ensure worker is running
        time.sleep(0.1)
        
        # Trigger the first signal handler call
        worker._signal_handler(None, None)
        
        # Now unblock the blpop call so the loop can check worker.running
        unblock_event.set()
        
        # Join the thread with a timeout
        worker_thread.join(timeout=2.0)
        
        # The thread should have terminated gracefully
        self.assertFalse(worker_thread.is_alive())
        self.assertTrue(worker.shutdown_event.is_set())
        self.assertFalse(worker.running)
