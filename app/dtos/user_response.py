from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        orm_mode = True  # Allows using SQLAlchemy models directly
