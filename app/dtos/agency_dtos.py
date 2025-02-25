from pydantic import BaseModel, EmailStr
import datetime

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

    class Config:
        orm_mode = True
