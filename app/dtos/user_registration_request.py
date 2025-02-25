# app/dtos/auth_dtos.py
from pydantic import BaseModel

class AdminRegistrationRequest(BaseModel):
    token: str
    username: str
    password: str
