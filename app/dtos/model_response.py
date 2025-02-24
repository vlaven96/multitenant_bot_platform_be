from typing import List, Optional
from dataclasses import dataclass
from pydantic import BaseModel
@dataclass
class ModelResponse(BaseModel):
    id: int
    name: str
    onlyfans_url: str


    def __repr__(self):
        return (
            f"ModelResponse("
            f"id={self.id},"
            f"name={self.name},"
            f"onlyfans_url={self.onlyfans_url})"
        )

    class Config:
        orm_mode = True
        from_attributes = True