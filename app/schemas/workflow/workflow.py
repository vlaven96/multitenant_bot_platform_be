from sqlalchemy import Integer, Column, String, Text, Enum

from app.database import Base
from sqlalchemy.orm import relationship

from app.models.workflow_status_enum import WorkflowStatusEnum


class Workflow(Base):
    __tablename__ = 'workflow'
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(Enum(WorkflowStatusEnum, name="workflow_status_enum"), default=WorkflowStatusEnum.ACTIVE, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Relationships
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.day_offset.asc()"  )
    snapchat_accounts = relationship("SnapchatAccount", back_populates="workflow")