from datetime import datetime

from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.dtos.account_execution_response import AccountExecutionResponse
from app.models.status_enum import StatusEnum


class ExecutionResponse(BaseModel):
    id: int
    type: str
    start_time: datetime
    end_time: Optional[datetime]
    triggered_by: str
    configuration: Dict[str, Any]
    status: StatusEnum
    account_executions: List[AccountExecutionResponse]

    class Config:
        orm_mode = True
        from_attributes = True