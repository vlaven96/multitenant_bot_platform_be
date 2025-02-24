from pydantic import BaseModel

class CookiesResponse(BaseModel):
    id: int
    data: str

    class Config:
        orm_mode = True
        from_attributes = True