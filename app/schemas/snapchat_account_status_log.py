from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.account_status_enum import AccountStatusEnum


class SnapchatAccountStatusLog(Base):
    __tablename__ = 'snapchat_account_status_log'

    id = Column(Integer, primary_key=True)
    snapchat_account_id = Column(Integer, ForeignKey('snapchat_account.id'), nullable=False)
    old_status = Column(Enum(AccountStatusEnum, name="account_status_enum"), nullable=True)
    new_status = Column(Enum(AccountStatusEnum, name="account_status_enum"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)

    snapchat_account = relationship("SnapchatAccount", back_populates="status_logs")
