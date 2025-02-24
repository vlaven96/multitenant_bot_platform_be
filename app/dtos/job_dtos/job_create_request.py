from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
from croniter import croniter
from datetime import datetime

from app.models.account_status_enum import AccountStatusEnum
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum


class JobCreateRequest(BaseModel):
    name: str = Field(..., example="Daily Backup")
    statuses: Optional[List[AccountStatusEnum]] = Field(
        ...,
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
    type: ExecutionTypeEnum = Field(
        ...,
        example="QUICK_ADDS",
        description="Type of execution for the job."
    )
    cron_expression: str = Field(
        ...,
        example="0 0 * * *",
        description="Cron expression to schedule the job."
    )
    configuration: Dict[str, Any] = Field(
        ...,
        example={"backup_path": "/var/backups/daily", "compress": True},
        description="Configuration settings for the job."
    )
    status: Optional[JobStatusEnum] = Field(
        JobStatusEnum.ACTIVE,
        description="Initial status of the job. Defaults to ACTIVE."
    )
    first_execution_time: Optional[datetime] = Field(
        None,
        example="2025-01-07T08:00:00",
        description="Optional datetime for the first execution time of the job."
    )

    @validator('cron_expression')
    def validate_cron(cls, v):
        if not croniter.is_valid(v):
            raise ValueError("Invalid cron expression.")
        return v
