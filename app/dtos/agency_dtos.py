from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

from app.dtos.subscription_response import SubscriptionResponse


class AgencyBase(BaseModel):
    name: str
    agency_email: EmailStr
    admin_role: str = "ADMIN"

class AgencyCreate(AgencyBase):
    pass

class AgencyResponse(BaseModel):
    id: int
    name: str
    created_at: datetime.datetime
    subscription: Optional[SubscriptionResponse] = None
    class Config:
        orm_mode = True

class AgencyCreateRequest(BaseModel):
    agency_name: str
    username: str
    password: str
    token: str