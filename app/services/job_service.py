# app/services/jobs_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import List, Optional
import json

from app.dtos.job_dtos.job_create_request import JobCreateRequest
from app.dtos.job_dtos.job_simplified_response import JobSimplifiedResponse
from app.dtos.job_dtos.job_update_request import JobUpdateRequest
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum
from app.schemas import SnapchatAccount
from app.schemas.executions.job import Job
from app.services.job_scheduler_manager import SchedulerManager
import logging

logger = logging.getLogger(__name__)

class JobsService:
    @staticmethod
    def create_job(db: Session, job_create: JobCreateRequest) -> Job:
        """
        Creates a new job, adds it to the database, and schedules it if active.
        """
        # Check if a job with the same name already exists
        existing_job = db.query(Job).filter(Job.name == job_create.name).first()
        if existing_job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job with this name already exists."
            )

        # Create a new Job instance
        try:
            db_job = Job(
                name=job_create.name,
                statuses=job_create.statuses,
                tags=job_create.tags,
                type=job_create.type,
                cron_expression=job_create.cron_expression,
                configuration=job_create.configuration,
                status=job_create.status or JobStatusEnum.ACTIVE,  # Default to ACTIVE if not provided
                start_date=job_create.first_execution_time,
                sources=job_create.sources
            )
            db.add(db_job)
            db.commit()
            db.refresh(db_job)
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job."
            )

        # Schedule the job if it's active
        if db_job.status == JobStatusEnum.ACTIVE:
            try:
                scheduler_manager = SchedulerManager.get_instance()
                scheduler_manager.add_job_to_scheduler(db_job)
            except Exception as e:
                # Optionally, handle scheduler exceptions (e.g., rollback the job creation)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to schedule job."
                )

        return db_job

    @staticmethod
    def update_job(db: Session, job_id: int, job_update: JobUpdateRequest) -> Job:
        """
        Updates an existing job's details and reschedules it based on status and cron_expression.
        """
        # Retrieve the job from the database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found."
            )

        # Update the job's attributes
        update_data = job_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in ['task_args', 'task_kwargs'] and value is not None:
                setattr(db_job, key, json.dumps(value))
            else:
                setattr(db_job, key, value)

        # Commit the changes to the database
        try:
            db.commit()
            db.refresh(db_job)
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job."
            )

        # Reschedule or unschedule the job based on its status
        try:
            scheduler_manager = SchedulerManager.get_instance()
            if db_job.status == JobStatusEnum.ACTIVE:
                scheduler_manager.add_job_to_scheduler(db_job)
            else:
                scheduler_manager.remove_job_from_scheduler(db_job.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reschedule job."
            )

        return db_job

    @staticmethod
    def delete_job(db: Session, job_id: int) -> None:
        """
        Performs a soft delete of a job by setting its status to STOPPED and removing it from the scheduler.
        """
        # Retrieve the job from the database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found."
            )
        initial_status = db_job.status
        if db_job.status == JobStatusEnum.DELETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is already stopped."
            )

        # Perform soft delete by setting status to STOPPED
        db_job.status = JobStatusEnum.DELETED

        # Commit the change to the database
        try:
            db.commit()
            db.refresh(db_job)
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop job."
            )

        if initial_status == JobStatusEnum.ACTIVE:
            # Remove the job from the scheduler
            try:
                scheduler_manager = SchedulerManager.get_instance()
                scheduler_manager.remove_job_from_scheduler(job_id)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to remove job from scheduler."
                )

    @staticmethod
    def update_job_status(db: Session, job_id: int, status_update: JobStatusEnum) -> Job:
        """
        Updates the status of a job and handles scheduling/removal accordingly.
        """
        # Retrieve the job from the database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found."
            )

        # Update the job's status
        db_job.status = status_update

        # Commit the change to the database
        try:
            db.commit()
            db.refresh(db_job)
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job status."
            )

        # Schedule or unschedule the job based on its new status
        try:
            scheduler_manager = SchedulerManager.get_instance()
            if db_job.status == JobStatusEnum.ACTIVE:
                scheduler_manager.add_job_to_scheduler(db_job)
            else:
                scheduler_manager.remove_job_from_scheduler(db_job.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update scheduler: {e}"
            )

        return db_job

    @staticmethod
    def get_job(db: Session, job_id: int) -> Job:
        """
        Retrieves a single job by its ID.
        """
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found."
            )
        return db_job

    @staticmethod
    def list_jobs(db: Session, status_filters: Optional[List[JobStatusEnum]] = None) -> List[Job]:
        """
        Retrieves a list of jobs, optionally filtered by status.
        """
        query = db.query(Job)
        if status_filters:
            query = query.filter(Job.status.in_(status_filters))
        query = query.order_by(Job.created_at.asc())
        return query.all()

    @staticmethod
    def restore_job(db: Session, job_id: int) -> Job:
        """
        Restores a stopped job by setting its status back to ACTIVE and rescheduling it.
        """
        # Retrieve the job from the database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found."
            )

        if db_job.status == JobStatusEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is already active."
            )

        # Restore the job by setting status to ACTIVE
        db_job.status = JobStatusEnum.ACTIVE

        # Commit the change to the database
        try:
            db.commit()
            db.refresh(db_job)
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore job."
            )

        # Reschedule the job
        try:
            scheduler_manager = SchedulerManager.get_instance()
            scheduler_manager.add_job_to_scheduler(db_job)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to schedule job."
            )

        return db_job

    @staticmethod
    def list_jobs_simplified(db: Session) -> List[JobSimplifiedResponse]:
        """
        Returns a simplified list of jobs (id and name).
        """
        jobs = db.query(Job.id, Job.name).all()
        return [JobSimplifiedResponse(id=job.id, name=job.name) for job in jobs]

    @staticmethod
    def get_snapchat_accounts_for_job(db: Session, job_id: int) -> List[SnapchatAccount]:
        """
        Retrieves all Snapchat accounts that match the given job's statuses, tags, and sources.
        """
        # Retrieve the job from the database
        job = db.query(Job).filter(Job.id == job_id, Job.status == JobStatusEnum.ACTIVE).first()
        if not job:
            logger.warning(f"Job ID {job_id} not found or is not active.")
            return {"detail": "Job not found or is not active."}

        logger.info(f"Checking type for {job.name}")
        account_ids = None
        if job.type != ExecutionTypeEnum.GENERATE_LEADS:
            logger.info(f"Checking type for {job.name}. And it enters here______________")

            # Extract statuses, tags, and sources
            statuses = job.statuses or []
            tags = job.tags or []
            sources = job.sources or []

            # Build the filter for SnapchatAccounts
            filters = []
            if statuses:
                filters.append(SnapchatAccount.status.in_(statuses))
            if tags:
                filters.append(SnapchatAccount.tags.contains(tags))
            if sources:
                filters.append(SnapchatAccount.account_source.in_(sources))

            # Query SnapchatAccounts based on filters
            accounts_query = db.query(SnapchatAccount).filter(*filters)
            return accounts_query.all()

        return []