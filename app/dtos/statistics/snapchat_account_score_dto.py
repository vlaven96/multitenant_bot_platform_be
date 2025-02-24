from pydantic import BaseModel
from typing import List

class SnapchatAccountScoreDTO(BaseModel):
    account_id: int
    username: str
    rejecting_rate: float
    conversation_rate: float
    conversion_rate: float
    score: float