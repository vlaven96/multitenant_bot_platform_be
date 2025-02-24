from pydantic import BaseModel
from typing import  List
from app.dtos.snapchat_account_simple_response import SnapchatAccountSimpleResponse

class ProxySimpleResponse(BaseModel):
    id: int
    host: str
    port: str
    proxy_username: str
    proxy_password: str

    class Config:
        orm_mode = True
        from_attributes = True
