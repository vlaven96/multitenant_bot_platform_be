from sqlalchemy import Column, Integer, String
from app.database import Base
from datetime import datetime

class SnapchatRejectedUser(Base):
    __tablename__ = 'snapchat_rejected_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    reason = Column(String, nullable=False)
    rejected_at = Column(String, default=datetime.utcnow, nullable=False)  # Optional for audit logging
