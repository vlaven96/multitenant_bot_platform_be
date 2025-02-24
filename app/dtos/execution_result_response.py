from typing import Dict, List, Optional
from pydantic import BaseModel

from app.dtos.execution_simple_response import ExecutionSimpleResponse


class ExecutionResultResponse(BaseModel):
    execution: ExecutionSimpleResponse  # You can use a specific schema for Execution if available
    results: Optional[Dict[str, int]]  # A mapping of status to count
    job_name: Optional[str]