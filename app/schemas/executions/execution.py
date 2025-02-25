from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Integer, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.execution_type_enum import ExecutionTypeEnum
from sqlalchemy.ext.mutable import MutableDict
from app.models.status_enum import StatusEnum


class Execution(Base):
    __tablename__ = 'execution'

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    type = Column(Enum(ExecutionTypeEnum), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    triggered_by = Column(String, nullable=False)
    configuration = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    status = Column(Enum(StatusEnum), nullable=False)

    # Relationship with AccountExecution
    account_executions = relationship("AccountExecution", back_populates="execution", cascade="all, delete-orphan")

    # Foreign key to Job
    job_id = Column(Integer, ForeignKey('jobs.id', ondelete="SET NULL"), nullable=True)

    # Relationship with Job
    job = relationship("Job", back_populates="executions")
    agency = relationship("Agency", back_populates="executions")

    __table_args__ = (
        Index('idx_execution_type', 'type'),
    )