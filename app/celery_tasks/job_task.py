# app/tasks/execute_job_task.py
from app.celery_tasks.executions_task import ExecutionTaskManager
import logging
from app.celery_app import celery
from app.database import SessionLocal
from datetime import datetime

from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum
from app.models.status_enum import StatusEnum
from app.schemas import SnapchatAccount
from app.schemas.executions.execution import Execution
from app.schemas.executions.job import Job
from app.event_listeners import log_status_change
from app.services.snapchat_account_statistics_service import SnapchatAccountStatisticsService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

class JobTaskManager:
    """
    Manages the execution of jobs by interacting with the database and Celery tasks.
    """

    @staticmethod
    @celery.task
    def execute_job(job_id: int):
        """
        Celery task to execute a job based on its ID.

        Args:
            job_id (int): The unique identifier of the job to execute.

        Returns:
            dict: Details of the execution after completion.
        """
        db = SessionLocal()
        try:
            # Retrieve the Job
            job = db.query(Job).filter(Job.id == job_id, Job.status == JobStatusEnum.ACTIVE).first()

            if not job:
                logger.warning(f"Job ID {job_id} not found or is not active.")
                return {"detail": "Job not found or is not active."}

            if not SubscriptionService.is_subscription_available(db, job.agency_id):
                message = f"Job {job.name} was not executed because subscription is expired."
                logger.info(message)
                return {"detail": message}
                # Create a new Execution record
            execution = Execution(
                type=job.type,  # Assuming Execution.type corresponds to Job.type
                triggered_by=job.name,
                configuration=job.configuration,
                status=StatusEnum.IN_PROGRESS,  # Assuming StatusEnum has IN_PROGRESS
                job_id=job_id,
                agency_id=job.agency_id
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            logger.info(f"Created Execution ID {execution.id} for Job ID {job_id}.")
            logger.info(f"Checking type for {job.name}")
            account_ids = None

            statuses = job.statuses or []
            tags = job.tags or []
            sources = job.sources or []

            if execution.type == ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS:
                snapchat_accounts = SnapchatAccountStatisticsService.get_accounts_by_thresholds(
                    session=db,
                    max_rejecting_rate_threshold=execution.configuration["max_rejection_rate"],
                    min_conversation_rate_threshold=execution.configuration["min_conversation_rate"],
                    min_conversion_rate_threshold=execution.configuration["min_conversion_rate"],
                    statuses=statuses,
                    tags=tags,
                    sources=sources,
                )
                account_ids = list(set(snapchat_account.id for snapchat_account in snapchat_accounts))
                if account_ids:
                    execution.configuration["requests"] = (
                            execution.configuration["requests"] / len(account_ids)
                    )
                else:
                    execution.configuration["requests"] = 0
                db.add(execution)
                db.commit()

            if job.type != ExecutionTypeEnum.GENERATE_LEADS and job.type != ExecutionTypeEnum.QUICK_ADDS_TOP_ACCOUNTS:
                logger.info(f"Checking type for {job.name}. And it enters here______________")
                # Build the filter for SnapchatAccounts
                filters = []
                if statuses:
                    filters.append(SnapchatAccount.status.in_(statuses))
                if tags:
                    filters.append(SnapchatAccount.tags.contains(tags))
                if sources:
                    filters.append(SnapchatAccount.account_source.in_(sources))

                if filters:
                    accounts_query = db.query(SnapchatAccount).filter(*filters)
                else:
                    accounts_query = db.query(SnapchatAccount)

                # Retrieve all matching account IDs
                account_ids = [account.id for account in accounts_query.all()]
                logger.info(f"Found {len(account_ids)} SnapchatAccounts for Job ID {job_id}.")

            # Dispatch the next Celery task with the Execution ID and SnapchatAccount IDs
            ExecutionTaskManager.execute_task_celery.delay(execution.id, account_ids)
            logger.info(f"Dispatched process_execution task for Execution ID {execution.id}.")

            return {
                "execution_id": execution.id,
                "job_id": job.id,
                "status": execution.status.value,
                "triggered_at": execution.start_time.isoformat() + 'Z'
            }

        except Exception as e:
            logger.error(f"Error executing Job ID {job_id}: {e}")
            # Optionally, update the Execution status to FAILED
            try:
                execution = db.query(Execution).filter(Execution.job_id == job_id).order_by(
                    Execution.id.desc()).first()
                if execution and execution.status == StatusEnum.IN_PROGRESS:
                    execution.status = StatusEnum.FAILED
                    execution.end_time = datetime.utcnow()
                    db.commit()
                    logger.info(f"Updated Execution ID {execution.id} status to FAILED.")
            except Exception as inner_e:
                logger.error(f"Error updating Execution status for Job ID {job_id}: {inner_e}")
            return {"detail": f"Error executing job: {e}"}

        finally:
            db.close()

