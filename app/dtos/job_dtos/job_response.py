from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
from croniter import croniter
from datetime import datetime

from app.models.account_status_enum import AccountStatusEnum
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum

class JobResponse(BaseModel):
    id: int = Field(..., example=1, description="Unique identifier for the job.")
    name: str = Field(..., example="Daily Backup")
    statuses: Optional[List[AccountStatusEnum]] = Field(
        ...,
        example=["ACTIVE", "INACTIVE"],
        description="List of account statuses applicable to the job."
    )
    tags: Optional[List[str]] = Field(
        None,
        example=["backup", "daily"],
        description="List of tags associated with the job."
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
        example="30 1 * * *",
        description="Cron expression to schedule the job."
    )
    configuration: Dict[str, Any] = Field(
        ...,
        example={"backup_path": "/var/backups/daily", "compress": False},
        description="Configuration settings for the job."
    )
    status: JobStatusEnum = Field(
        ...,
        example="ACTIVE",
        description="Current status of the job."
    )
    created_at: datetime = Field(
        ...,
        example="2025-01-05T00:00:00Z",
        description="Timestamp when the job was created."
    )
    start_date: Optional[datetime] = Field(
        ...,
        example="2025-01-05T00:00:00Z",
        description="Timestamp when the job was created."
    )

    class Config:
        orm_mode = True
