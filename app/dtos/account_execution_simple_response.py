from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class AccountExecutionSimpleResponse(BaseModel):
    id: int
    status: str
    message: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]

    class Config:
        from_attributes = True
