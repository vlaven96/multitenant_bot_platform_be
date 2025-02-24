from pydantic import BaseModel

class JobSimplifiedResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
