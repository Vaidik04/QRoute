import asyncio
import threading
from typing import Dict, Any, Callable, Coroutine
import logging

logger = logging.getLogger("qtransit")

class TaskWorkerPool:
    """Lightweight asynchronous background task pool for executing optimization & simulation jobs."""

    def __init__(self):
        self._loop = None
        self._thread = None
        self._is_running = False

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("TaskWorkerPool background thread started successfully.")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def submit_task(self, coro: Coroutine):
        """Submit an async task to the background event loop."""
        if self._loop and self._is_running:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            # Fallback inline creation
            asyncio.create_task(coro)

    def stop(self):
        if self._loop and self._is_running:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._is_running = False

worker_pool = TaskWorkerPool()
