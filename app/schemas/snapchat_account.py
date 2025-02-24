from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList
from app.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func

from app.models.account_status_enum import AccountStatusEnum

class SnapchatAccount(Base):
    __tablename__ = 'snapchat_account'
    
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    snapchat_id = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, nullable=True)
    email_password = Column(String, nullable=True)
    snapchat_link = Column(String, nullable=False)
    two_fa_secret = Column(String, nullable=True)
    creation_date = Column(DateTime, default=func.now(), nullable=False)
    # Set added_to_system_date to default on creation but allow explicit updates
    added_to_system_date = Column(DateTime, default=func.now(), nullable=False)
    status = Column(
        Enum(AccountStatusEnum, name="account_status_enum"),  # Use the SQLAlchemy Enum type
        default=AccountStatusEnum.RECENTLY_INGESTED,
        nullable=False
    )
    tags = Column(MutableList.as_mutable(ARRAY(String)), nullable=True)
    account_source = Column(String, nullable=False)

    proxy_id = Column(Integer, ForeignKey('proxy.id', ondelete="SET NULL"), nullable=True)
    proxy = relationship(
        "Proxy",
        back_populates="snapchat_accounts",
        foreign_keys=[proxy_id]  # Explicitly define the foreign key
    )
    device = relationship("Device", back_populates="snapchat_account", uselist=False, cascade="all, delete-orphan")
    cookies = relationship("Cookies", back_populates="snapchat_account", uselist=False, cascade="all, delete-orphan")
    account_executions = relationship("AccountExecution", back_populates="snapchat_account",
                                      cascade="all, delete-orphan")
    model_id = Column(Integer, ForeignKey('model.id', ondelete="SET NULL"), nullable=True)
    model = relationship("Model", back_populates="snapchat_accounts")

    chatbot_id = Column(Integer, ForeignKey('chatbot.id', ondelete="SET NULL"), nullable=True)
    chat_bot = relationship("ChatBot", back_populates="snapchat_accounts")

    status_logs = relationship("SnapchatAccountStatusLog", back_populates="snapchat_account",
                               cascade="all, delete-orphan")

    # Optional one-to-one relationship with SnapchatAccountLogin
    snapchat_account_login = relationship(
        "SnapchatAccountLogin",
        back_populates="snapchat_account",
        uselist=False,
        cascade="all, delete-orphan"
    )

    stats = relationship("SnapchatAccountStats", back_populates="snapchat_account", uselist=False,
                         cascade="all, delete-orphan")

    workflow_id = Column(Integer, ForeignKey('workflow.id', ondelete="SET NULL"), nullable=True)

    # Relationship back to workflow
    workflow = relationship("Workflow", back_populates="snapchat_accounts")

    agency = relationship("Agency", back_populates="snapchat_accounts")

    __table_args__ = (
        Index('idx_snapchat_account_status', 'status'),
    )
