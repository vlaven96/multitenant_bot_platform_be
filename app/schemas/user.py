from sqlalchemy import Column, Integer, String, Boolean, Integer, ForeignKey, Enum
from app.database import Base
from sqlalchemy.orm import relationship
import enum

class UserRole(enum.Enum):
    GLOBAL_ADMIN = "GLOBAL_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable = True)
    password = Column(String)

    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)

    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True)
    agency = relationship("Agency", back_populates="users", foreign_keys=[agency_id])