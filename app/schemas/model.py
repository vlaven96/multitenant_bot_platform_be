from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base
from sqlalchemy.orm import relationship

class Model(Base):
    __tablename__ = 'model'
    
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    name = Column(String, nullable=False)
    onlyfans_url = Column(String, nullable=False)

    snapchat_accounts = relationship("SnapchatAccount", back_populates="model", cascade="all, delete-orphan")
    snapchat_allowed_users = relationship(
        "SnapchatAllowedUser",
        back_populates="model",
        passive_deletes=True
    )
    agency = relationship("Agency", back_populates="models")