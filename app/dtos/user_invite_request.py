from pydantic import BaseModel, EmailStr

class UserInviteRequest(BaseModel):
    email: EmailStr