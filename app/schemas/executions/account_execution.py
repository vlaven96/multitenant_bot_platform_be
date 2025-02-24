from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Integer

from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.status_enum import StatusEnum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Integer, Index

class AccountExecution(Base):
    __tablename__ = 'account_execution'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ExecutionTypeEnum), nullable=False)
    execution_id = Column(Integer, ForeignKey("execution.id"), nullable=False)
    snap_account_id = Column(Integer, ForeignKey("snapchat_account.id"), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False)
    result = Column(JSON, default=None, nullable=True)
    message = Column(String, nullable=True)

    # Relationships
    execution = relationship("Execution", back_populates="account_executions")
    snapchat_account = relationship("SnapchatAccount", back_populates="account_executions")
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_account_execution_type', 'type'),
    )

    @property
    def snapchat_account_username(self):
        return self.snapchat_account.username if self.snapchat_account else None
