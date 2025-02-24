from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    service_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
