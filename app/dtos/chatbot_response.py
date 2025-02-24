from dataclasses import dataclass
from pydantic import BaseModel
@dataclass
class ChatBotResponse(BaseModel):
    id: int
    type: str
    token: str

    def __repr__(self):
        return (
            f"ChatBotResponse("
            f"id={self.id},"
            f"type={self.type},"
            f"token={self.token})"
        )

    class Config:
        orm_mode = True
        from_attributes = True