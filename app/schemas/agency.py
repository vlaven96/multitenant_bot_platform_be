from sqlalchemy import Column, Integer, String
from app.database import Base
from sqlalchemy.orm import relationship

class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # Relationships
    snapchat_accounts = relationship("SnapchatAccount", back_populates="agency", cascade="all, delete")
    proxies = relationship("Proxy", back_populates="agency", cascade="all, delete")
    users = relationship("User", back_populates="agency", cascade="all, delete")