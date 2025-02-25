from sqlalchemy import Column, Integer, JSON, ForeignKey, Integer
from app.database import Base
from sqlalchemy.orm import relationship

class Cookies(Base):
    __tablename__ = 'cookies'
    
    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)
    snapchat_account_id = Column(Integer, ForeignKey('snapchat_account.id'), nullable=False, unique=True)

    snapchat_account = relationship("SnapchatAccount", back_populates="cookies")