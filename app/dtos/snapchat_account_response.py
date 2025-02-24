from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from typing import  List
from app.dtos.account_execution_simple_response import AccountExecutionSimpleResponse
from app.dtos.chatbot_response import ChatBotResponse
from app.dtos.cookies_response import CookiesResponse
from app.dtos.device_response import DeviceResponse
from app.dtos.model_response import ModelResponse
from app.dtos.proxy_response import ProxyResponse
from app.dtos.proxy_simple_response import ProxySimpleResponse
from app.dtos.workflow_dtos import WorkflowSimplifiedNameResponse


class SnapchatAccountResponse(BaseModel):
    id: int
    username: str
    password: str
    snapchat_link: str
    two_fa_secret: Optional[str]
    creation_date: datetime
    added_to_system_date: datetime
    status: str
    proxy: Optional[ProxySimpleResponse]
    device: Optional[DeviceResponse]
    cookies: Optional[CookiesResponse]
    account_executions: Optional[List[AccountExecutionSimpleResponse]] = None
    model: ModelResponse
    chat_bot: ChatBotResponse
    tags: Optional[List[str]]
    account_source: str
    workflow: Optional[WorkflowSimplifiedNameResponse]

    class Config:
        orm_mode = True
        from_attributes = True

class SnapchatAccountResponseV2(BaseModel):
    id: int
    username: str
    password: str
    snapchat_link: str
    two_fa_secret: Optional[str]
    creation_date: datetime
    added_to_system_date: datetime
    status: str
    proxy: Optional[ProxySimpleResponse]
    device: Optional[DeviceResponse]
    cookies: Optional[CookiesResponse]
    model: Optional[ModelResponse]
    chat_bot: Optional[ChatBotResponse]
    tags: Optional[List[str]]
    account_source: str
    workflow: Optional[WorkflowSimplifiedNameResponse]

    class Config:
        orm_mode = True
        from_attributes = True
