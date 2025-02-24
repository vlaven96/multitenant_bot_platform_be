from pydantic import BaseModel
from app.models.job_status_enum import JobStatusEnum

class JobStatusUpdateRequest(BaseModel):
    status_update: JobStatusEnum