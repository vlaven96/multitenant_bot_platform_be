# app/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import json
from croniter import croniter
from datetime import datetime, timedelta
import logging

from app.celery_tasks.executions_task import ExecutionTaskManager
from app.celery_tasks.job_task import JobTaskManager
from app.celery_tasks.unlock_accounts_job import UnlockAccountsTaskManager
from app.celery_tasks.workflow_task import WorkflowTaskManager
from app.schemas.executions.job import Job

logger = logging.getLogger(__name__)

class SchedulerManager:
    """
    A class to manage APScheduler for scheduling and unscheduling jobs.
    """
    _instance = None

    def __init__(self, timezone: str = 'UTC'):
        if SchedulerManager._instance is not None:
            raise Exception("This class is a singleton! Use `SchedulerManager.get_instance()` to access it.")

        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.scheduler.start()
        logger.info("APScheduler initialized and started.")
        SchedulerManager._instance = self

    @staticmethod
    def get_instance():
        if SchedulerManager._instance is None:
            SchedulerManager._instance = SchedulerManager()
        return SchedulerManager._instance

    def parse_cron_expression(self, cron_expression: str) -> dict:
        """
        Validates and parses a standard 5-field cron expression.
        Returns a dictionary of cron parameters.

        Args:
            cron_expression (str): The cron expression to validate and parse.

        Returns:
            dict: Parsed cron parameters.

        Raises:
            ValueError: If the cron expression is invalid.
        """
        try:
            # Validate cron expression
            if not croniter.is_valid(cron_expression):
                raise ValueError("Invalid cron expression.")

            parts = cron_expression.strip().split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have exactly 5 fields.")

            minute, hour, day, month, day_of_week = parts
            return {
                'minute': minute,
                'hour': hour,
                'day': day,
                'month': month,
                'day_of_week': day_of_week,
            }
        except Exception as e:
            logger.error(f"Error parsing cron expression '{cron_expression}': {e}")
            raise

    def trigger_celery_task(self, job_id: int):
        """
        Function to trigger the Celery task associated with a Job.
        This function is scheduled by APScheduler.

        Args:
            job_id (int): The unique identifier of the job.
        """
        try:
            # Dispatch the Celery task with job_id
            JobTaskManager.execute_job.delay(job_id)
            logger.info(f"Dispatched Celery task for Job ID {job_id}.")
        except Exception as e:
            logger.error(f"Error dispatching Celery task for Job ID {job_id}: {e}")

    def trigger_celery_workflow(self):
        """
        Function to trigger the Celery task associated with a Job.
        This function is scheduled by APScheduler.

        Args:
            job_id (int): The unique identifier of the job.
        """
        try:
            # Dispatch the Celery task with job_id
            WorkflowTaskManager.execute_workflows.delay()
            logger.info(f"Dispatched Celery Workflow Job.")
        except Exception as e:
            logger.error(f"Error dispatching Celery Workflow Job: {e}")

    def trigger_celery_unlock_accounts(self):
        """
        Function to trigger the Celery task associated with a Job.
        This function is scheduled by APScheduler.

        Args:
            job_id (int): The unique identifier of the job.
        """
        try:
            # Dispatch the Celery task with job_id
            UnlockAccountsTaskManager.unlock_accounts.delay()
            logger.info(f"Dispatched Celery Unlock Account Job.")
        except Exception as e:
            logger.error(f"Error dispatching Celery Unlock Account Job: {e}")

    def add_job_to_scheduler(self, job: Job):
        """
        Adds a job to APScheduler based on the Job model.

        Args:
            job (Job): The job instance from the database.

        Raises:
            Exception: If adding the job to the scheduler fails.
        """
        try:
            # Parse the cron expression
            cron_params = self.parse_cron_expression(job.cron_expression)

            # Create a CronTrigger
            trigger = CronTrigger(**cron_params, timezone=self.scheduler.timezone)

            if job.start_date is None:
                next_run_time = None  # Don't provide next_run_time if start_date is None
            elif job.start_date > datetime.utcnow():
                next_run_time = job.start_date  # Use job.start_date if it is in the future
            else:
                time_difference = job.start_date - datetime.utcnow()
                if 0 <= time_difference.total_seconds() <= 70:  # Within 3 minutes
                    next_run_time = datetime.utcnow() + timedelta(seconds=5)
                else:
                    next_run_time = None

            # Add the job to the scheduler
            if next_run_time:
                self.scheduler.add_job(
                    func=self.trigger_celery_task,
                    trigger=trigger,
                    args=[job.id],
                    id=str(job.id),  # Unique identifier for the job
                    replace_existing=True,
                    name=job.name,
                    next_run_time=next_run_time
                )
            else:
                self.scheduler.add_job(
                    func=self.trigger_celery_task,
                    trigger=trigger,
                    args=[job.id],
                    id=str(job.id),  # Unique identifier for the job
                    replace_existing=True,
                    name=job.name,
                )
            logger.info(f"Added Job ID {job.id} to scheduler with cron '{job.cron_expression}' and start time {next_run_time}.")
        except Exception as e:
            logger.error(f"Failed to add Job ID {job.id} to scheduler: {e}")
            raise

    def remove_job_from_scheduler(self, job_id: int):
        """
        Removes a job from APScheduler.

        Args:
            job_id (int): The unique identifier of the job to remove.

        Raises:
            Exception: If removing the job from the scheduler fails.
        """
        try:
            self.scheduler.remove_job(str(job_id))
            logger.info(f"Removed Job ID {job_id} from scheduler.")
        except Exception as e:
            logger.error(f"Failed to remove Job ID {job_id} from scheduler: {e}")
            raise

    def shutdown_scheduler(self):
        """
        Shuts down the scheduler gracefully, removing all jobs first.
        """
        try:
            self.scheduler.remove_all_jobs()  # Remove all jobs before shutdown
            logger.info("All jobs removed from scheduler.")
        except Exception as e:
            logger.error(f"Error removing jobs: {e}")

        self.scheduler.shutdown()
        logger.info("APScheduler shut down gracefully.")

    def initialize_scheduler(self, jobs: list):
        """
        Loads and schedules all active jobs from the provided list.

        Args:
            jobs (list): List of active jobs to schedule.
        """
        for job in jobs:
            try:
                self.add_job_to_scheduler(job)
            except Exception as e:
                logger.error(f"Error scheduling job {job.id}: {e}")
        logger.info("Jobs scheduled: ")
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"* {job}")

    def initialize_workflow_job(self):
        """
        Schedules the `WorkflowTaskManager.execute_workflows` task to run daily at 1 AM.
        """
        try:
            # Create a CronTrigger for daily execution at 1 AM
            trigger = CronTrigger(hour=1, minute=0, timezone=self.scheduler.timezone)

            # Add the workflow execution task to the scheduler
            self.scheduler.add_job(
                func=self.trigger_celery_workflow,
                trigger=trigger,
                id="workflow_execution",  # Unique identifier for the workflow job
                replace_existing=True,  # Replace existing job if it exists
                name="Daily Workflow Execution",
            )

            logger.info("Scheduled `WorkflowTaskManager.execute_workflows` to run daily at 1 AM.")
        except Exception as e:
            logger.error(f"Failed to schedule workflow execution job: {e}")
            raise

    def initialize_unlock_accounts_job(self):
        """
        Schedules the `UnlockAccountsTaskManager.unlock_accounts` task to run daily at 2 AM.
        """
        try:
            trigger = CronTrigger(hour=2, minute=0, timezone=self.scheduler.timezone)
            # Add the workflow execution task to the scheduler
            self.scheduler.add_job(
                func=self.trigger_celery_unlock_accounts,
                trigger=trigger,
                id="unlock_accounts",  # Unique identifier for the workflow job
                replace_existing=True,  # Replace existing job if it exists
                name="Unlock Account Job",
            )

            logger.info("Scheduled `UnlockAccountsTaskManager.unlock_accounts` to run daily at 2 AM.")
        except Exception as e:
            logger.error(f"Failed to schedule unlock accounts job: {e}")
            raise



    def shutdown_scheduler(self):
        """
        Shuts down the scheduler gracefully.
        """
        self.scheduler.shutdown()
        logger.info("APScheduler shut down gracefully.")
