from app.models.workflow_step_type_enum import WorkflowStepTypeEnum
from sqlalchemy import Integer, Column, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base

class WorkflowStep(Base):
    __tablename__ = "workflowstep"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(
        Integer,
        ForeignKey('workflow.id', ondelete="CASCADE"),  # Ensure steps are deleted when a workflow is deleted
        nullable=False
    )
    day_offset = Column(Integer, nullable=False, comment="Days from start of workflow when this step executes")
    action_type = Column(
        Enum(WorkflowStepTypeEnum, name="step_type_enum"),  # Use the SQLAlchemy Enum type
        nullable=False
    )
    action_value = Column(String(255), comment="Parameters for the action")

    # Relationship back to workflow
    workflow = relationship("Workflow", back_populates="steps")