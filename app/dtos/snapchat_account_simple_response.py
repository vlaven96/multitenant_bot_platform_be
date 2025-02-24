from pydantic import BaseModel

class SnapchatAccountSimpleResponse(BaseModel):
    id: int
    username: str
    status: str

    class Config:
        orm_mode = True
        from_attributes = True