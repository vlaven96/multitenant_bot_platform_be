# my_project/app/celery_app.py
import os
import sys
from celery import Celery
from logging_config import setup_logging
import logging
from celery.signals import worker_process_init, after_setup_task_logger

protobuf_path = os.path.abspath("app/protos")
if protobuf_path not in sys.path:
    sys.path.append(protobuf_path)

setup_logging()
logger = logging.getLogger(__name__)

from app.services.key_vault.key_vault_manager import KeyVaultManager

# Load API key only once when Celery worker starts
if not os.getenv("SNAPKAT_API_KEY"):
    print("Fetching SNAPKAT_API_KEY from Key Vault (Celery Worker)...")
    os.environ["SNAPKAT_API_KEY"] = KeyVaultManager.get_secret("SNAPKAT_API_KEY")
# Configure the Celery instance:
# - broker: e.g., Redis or RabbitMQ URL
# - backend: for storing task results (optional but recommended)
celery = Celery(
    "dpa_bot_celery_mt",
    broker="redis://localhost:6379/1",   # or "amqp://localhost" for RabbitMQ
    backend="redis://localhost:6379/1",
)
celery.conf.timezone = "UTC"
# Optional: Load config from a configuration object or file
celery.conf.update(
    task_track_started=True,
    result_expires=3600,
    # additional Celery settings
)

# from app.celery_tasks.job_task import JobTaskManager
# from app.celery_tasks.executions_task import ExecutionTaskManager
celery.autodiscover_tasks(["app.celery_tasks"])

@worker_process_init.connect
def configure_worker_logging(**kwargs):
    setup_logging()
    logger.info("✅ Worker logging configured.")

@after_setup_task_logger.connect
def configure_task_logger(logger, *args, **kwargs):
    setup_logging()
    logger.info("✅ after_setup_task_logger: Task logging configured.")