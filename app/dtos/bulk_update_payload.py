# app/dtos/bulk_update_dto.py
from pydantic import BaseModel
from typing import List, Optional

class BulkUpdatePayload(BaseModel):
    account_ids: List[int]
    status: Optional[str] = None
    tags_to_add: Optional[List[str]] = None
    tags_to_remove: Optional[List[str]] = None
    model_id: Optional[int] = None
    chat_bot_id: Optional[int] = None
