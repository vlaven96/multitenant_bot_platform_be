from fastapi import FastAPI, APIRouter
import uvicorn
import sys
import os
from app.models.job_status_enum import JobStatusEnum
from app.routers import auth_router
from app.routers import admin_router
from app.routers import proxy_router
from app.routers import snapchat_account_router
from app.routers import execution_router
from app.routers import api_keys_router
from app.routers import cookie_router
from app.routers import model_router
from app.routers import chatbot_router
from app.routers import tags_router
from app.routers import job_router
from app.routers import workflow_router
from app.routers import  validator_router
from app.routers import statistic_router
from app.routers import agency_router
from app.routers import subscription_router
from app.services.job_scheduler_manager import SchedulerManager
from app.utils.database_resource_creator import create_default_admin, associate_accounts_with_model, \
    associate_accounts_with_chatbot, create_global_admin
from app.event_listeners import log_status_change
from app.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import *
from app.database import SessionLocal

from app.utils.loggig_manager import LoggingManager
from logging_config import setup_logging
import logging

protobuf_path = os.path.abspath("app/protos")
if protobuf_path not in sys.path:
    sys.path.append(protobuf_path)

setup_logging()

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
app = FastAPI(debug=True)
origins = [
    "http://localhost:5173",  # React development server
    "http://127.0.0.1:3000",  # Alternate localhost
    "http://localhost:4173",
    "http://138.201.226.205:5177",  # prod
    "https://138.201.226.205:5177",  # prod
    "http://138.201.226.205:5178",  # prod
    "https://138.201.226.205:5178",  # prod
    "https://snepflow.com",
    "http://snepflow.com",
    "http://api.snepflow.com",
    "https://api.snepflow.com",
]


@app.on_event("startup")
async def startup_event():
    # Initialize the LoggingManager to start the worker
    logging_manager = LoggingManager.get_instance()
    logging_manager.start_worker()


    # Initialize the SchedulerManager and schedule active jobs
    db = SessionLocal()
    try:
        # Fetch all active jobs from the database
        scheduler_manager = SchedulerManager.get_instance()

        # Schedule the daily workflow execution at 1 AM
        scheduler_manager.initialize_workflow_job()
        logger.info("Scheduled daily workflow execution at 1 AM.")

        scheduler_manager.initialize_unlock_accounts_job()
        logger.info("Scheduled daily unlock accounts job at 2 AM.")

        active_jobs = db.query(Job).filter(Job.status == JobStatusEnum.ACTIVE).all()
        scheduler_manager.initialize_scheduler(active_jobs)
        logger.info(f"Initialized scheduler with {len(active_jobs)} active jobs.")
    except Exception as e:
        logger.error(f"Error initializing scheduler with existing jobs: {e}")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI shutdown event handler.
    Shuts down the SchedulerManager and LoggingManager gracefully.
    """
    # Shut down the SchedulerManager
    scheduler_manager = SchedulerManager.get_instance()
    scheduler_manager.shutdown_scheduler()
    logger.info("SchedulerManager has been shut down.")

    # Shut down the LoggingManager if necessary
    logging_manager = LoggingManager.get_instance()
    await logging_manager.stop_worker()
    logger.info("LoggingManager has been shut down.")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies and headers like Authorization
    allow_methods=["*"],  # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Create main_router with "/agency/{agency_id}" for multi-tenant routes
main_router = APIRouter(prefix="/agencies/{agency_id}")

# Include multi-tenant routers inside `main_router`
main_router.include_router(snapchat_account_router.router)
main_router.include_router(proxy_router.router)
main_router.include_router(execution_router.router)
main_router.include_router(model_router.router)
main_router.include_router(chatbot_router.router)
main_router.include_router(tags_router.router)
main_router.include_router(job_router.router)
main_router.include_router(workflow_router.router)
main_router.include_router(validator_router.router)
main_router.include_router(statistic_router.router)
main_router.include_router(admin_router.router)
main_router.include_router(subscription_router.router)
# Include the agency router separately (no agency_id prefix needed)
app.include_router(agency_router.router)  # Global agency management

# 🚀 FIX: Add `main_router` to `app` so nested routes are visible
app.include_router(main_router)

# Include non-agency-scoped routes
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(api_keys_router.router)
app.include_router(cookie_router.router)

create_global_admin()
@app.get("/")
def read_root():
    return {"message": "FastAPI Authentication System"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
