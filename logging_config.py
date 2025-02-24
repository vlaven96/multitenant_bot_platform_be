# logging_config.py
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os

os.makedirs("./logs", exist_ok=True)

LOG_FILENAME = "./logs/bot_platform.log"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file_handler": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": LOG_FILENAME,
            "maxBytes": 10_000_000,  # 5 MB
            "backupCount": 10,
        },
    },
    "loggers": {
        # Root logger
        "": {
            "handlers": ["default", "file_handler"],
            "level": "INFO",
        },
        # Uvicorn logger, which includes FastAPI logs
        "uvicorn": {
            "handlers": ["default", "file_handler"],
            "level": "INFO",
            "propagate": False
        },
        # Celery logger
        "celery": {
            "handlers": ["default", "file_handler"],
            "level": "INFO",
            "propagate": False
        },
    },
}

def setup_logging():
    """Call this function at application startup to set up logging."""
    logging.config.dictConfig(LOGGING_CONFIG)
