from pydantic import BaseModel
from typing import  List
from app.dtos.snapchat_account_simple_response import SnapchatAccountSimpleResponse

class ProxyResponse(BaseModel):
    id: int
    proxy_username: str
    proxy_password: str
    host: str
    snapchat_accounts: List[SnapchatAccountSimpleResponse] = []
    port: str

    class Config:
        orm_mode = True
        from_attributes = True
