from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class AccountExecutionResponse(BaseModel):
    id: int
    type: str
    snap_account_id: int
    status: str
    result: Optional[dict]
    message: Optional[str]
    snapchat_account_username: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True

    @validator("message", pre=True, always=True)
    def trim_message(cls, value):
        if value and len(value) > 1000:
            return value[:1000] + "..."
        return value