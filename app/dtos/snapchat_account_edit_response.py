from pydantic import BaseModel

from app.dtos.chatbot_response import ChatBotResponse
from app.dtos.model_response import ModelResponse
from app.dtos.proxy_response import ProxyResponse
from app.dtos.proxy_simple_response import ProxySimpleResponse
from app.dtos.snapchat_account_response import SnapchatAccountResponseV2
from typing import List, Optional

from app.dtos.workflow_dtos import WorkflowSimplifiedNameResponse


class SnapchatAccountEditResponse(BaseModel):
    account: SnapchatAccountResponseV2
    proxies: List[ProxySimpleResponse]
    models: List[ModelResponse]
    chat_bots: List[ChatBotResponse]
    statuses: List[str]
    tags: List[str]
    workflows: List[WorkflowSimplifiedNameResponse]


