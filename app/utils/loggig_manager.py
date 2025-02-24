import asyncio
from app.utils.http_request_handler import HttpRequestHandler
import logging

logger = logging.getLogger(__name__)

class LoggingManager:
    _instance = None

    def __init__(self, redis_url="redis://localhost:6379/0"):
        if LoggingManager._instance is not None:
            raise Exception("This class is a singleton! Use `LoggingManager.get_instance()` to access it.")

        # Initialize the shared logging queue and handler
        self.http_handler = HttpRequestHandler(redis_url=redis_url)
        self.worker_task = None

    @staticmethod
    def get_instance():
        if LoggingManager._instance is None:
            LoggingManager._instance = LoggingManager()
        return LoggingManager._instance

    def start_worker(self):
        """Start the logging worker in the current event loop."""
        self.worker_task = asyncio.create_task(self.http_handler.log_worker())
        logger.info("Logging worker started.")

    async def stop_worker(self):
        """Gracefully cancel the logging worker task."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                logger.info("Logging worker task cancelled.")
