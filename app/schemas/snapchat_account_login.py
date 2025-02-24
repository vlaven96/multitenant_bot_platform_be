from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship


class SnapchatAccountLogin(Base):
    __tablename__ = 'snapchat_account_login'

    id = Column(Integer, primary_key=True)
    snap_account_id = Column(Integer, ForeignKey('snapchat_account.id', ondelete="CASCADE"), nullable=False)
    auth_token = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    mutable_username = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationship with SnapchatAccount (one-to-one)
    snapchat_account = relationship(
        "SnapchatAccount",
        back_populates="snapchat_account_login",
        uselist=False  # One-to-one relationship
    )
