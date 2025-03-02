from sqlalchemy import Column, Integer, String, Enum, ARRAY, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.account_status_enum import AccountStatusEnum
from app.models.execution_type_enum import ExecutionTypeEnum
from app.models.job_status_enum import JobStatusEnum


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    statuses = Column(ARRAY(Enum(AccountStatusEnum, name="account_status_enum")), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    sources = Column(ARRAY(String), nullable=True)
    type = Column(Enum(ExecutionTypeEnum, name="executiontypeenum"), nullable=False)
    configuration = Column(JSON, nullable=False)
    cron_expression = Column(String, nullable=False)
    status = Column(Enum(JobStatusEnum, name="job_status_enum"), default=JobStatusEnum.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_date = Column(DateTime(timezone=False), nullable=True)
    # Relationship with Execution
    executions = relationship("Execution", back_populates="job", cascade="all, delete-orphan")
    agency = relationship("Agency", back_populates="jobs")
