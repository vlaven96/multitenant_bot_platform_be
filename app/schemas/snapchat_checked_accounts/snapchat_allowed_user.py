from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class SnapchatAllowedUser(Base):
    __tablename__ = 'snapchat_allowed_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    last_requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    user_id = Column(String, unique=True, nullable=True)
    suggestion_token = Column(String, unique=False, nullable=True)

    # Reference to the Model database object
    model_id = Column(Integer, ForeignKey('model.id', ondelete="SET NULL"), nullable=True)
    model = relationship("Model", back_populates="snapchat_allowed_users")
