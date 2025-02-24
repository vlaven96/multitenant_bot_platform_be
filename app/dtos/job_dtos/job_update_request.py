from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
from croniter import croniter
from datetime import datetime

from app.models.account_status_enum import AccountStatusEnum
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum

class JobUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        None,
        example="Daily Backup",
        description="Unique name for the job."
    )
    statuses: Optional[List[AccountStatusEnum]] = Field(
        None,
        example=["ACTIVE", "INACTIVE"],
        description="List of account statuses applicable to the job."
    )
    tags: Optional[List[str]] = Field(
        None,
        example=["backup", "daily"],
        description="Optional list of tags associated with the job."
    )
    sources: Optional[List[str]] = Field(
        None,
        example=["backup", "daily"],
        description="List of sources associated with the job."
    )
    type: Optional[ExecutionTypeEnum] = Field(
        None,
        example="QUICK_ADDS",
        description="Type of execution for the job."
    )
    cron_expression: Optional[str] = Field(
        None,
        example="30 1 * * *",
        description="Cron expression to schedule the job."
    )
    task_name: Optional[str] = Field(
        None,
        example="app.celery_tasks.backup_task.BackupTaskManager.execute_backup",
        description="Path to the Celery task to execute."
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        example={"backup_path": "/var/backups/daily", "compress": False},
        description="Configuration settings for the job."
    )
    status: Optional[JobStatusEnum] = Field(
        None,
        description="Status of the job."
    )
    first_execution_time: Optional[datetime] = Field(
        None,
        example="2025-01-07T08:00:00",
        description="Optional datetime for the first execution time of the job."
    )

    @validator('cron_expression')
    def validate_cron(cls, v):
        if v is not None and not croniter.is_valid(v):
            raise ValueError("Invalid cron expression.")
        return v
