from sqlalchemy import Column, String, DateTime, Boolean
from app.database import Base
from datetime import datetime
class InvitationToken(Base):
    __tablename__ = 'invitation_tokens'
    token = Column(String, primary_key=True)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)