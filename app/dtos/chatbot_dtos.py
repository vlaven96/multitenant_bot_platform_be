from pydantic import BaseModel
from typing import Optional, List

from app.models.chat_bot_type_enum import ChatBotTypeEnum

class ChatBotCreate(BaseModel):
    type: ChatBotTypeEnum
    token: str

class ChatBotUpdate(BaseModel):
    type: Optional[ChatBotTypeEnum] = None
    token: Optional[str] = None

class ChatBotResponse(BaseModel):
    id: int
    type: ChatBotTypeEnum
    token: str

    class Config:
        orm_mode = True
