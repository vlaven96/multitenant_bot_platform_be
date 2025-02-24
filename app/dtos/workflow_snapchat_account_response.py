from typing import Optional

from pydantic import BaseModel

from app.dtos.snapchat_account_simple_response import SnapchatAccountSimpleResponse


class WorkflowSnapchatAccountResponse(BaseModel):
    snapchat_account: SnapchatAccountSimpleResponse
    last_executed_step: Optional[int]