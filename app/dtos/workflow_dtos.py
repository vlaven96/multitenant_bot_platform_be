from typing import List, Optional

from pydantic import BaseModel

from app.models.workflow_status_enum import WorkflowStatusEnum
from app.models.workflow_step_type_enum import WorkflowStepTypeEnum


# Requests
class WorkflowStepCreateRequest(BaseModel):
    day_offset: int
    action_type: WorkflowStepTypeEnum
    action_value: str


class WorkflowStepUpdateRequest(BaseModel):
    id: Optional[int] = None
    day_offset: int
    action_type: WorkflowStepTypeEnum
    action_value: str


class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str]
    status: WorkflowStatusEnum = WorkflowStatusEnum.ACTIVE
    steps: List[WorkflowStepCreateRequest]


# Responses
class WorkflowUpdateRequest(BaseModel):
    id: int
    name: Optional[str]
    description: Optional[str]
    status: WorkflowStatusEnum
    steps: List[WorkflowStepUpdateRequest]


class WorkflowStepResponse(BaseModel):
    id: int
    day_offset: int
    action_type: WorkflowStepTypeEnum
    action_value: Optional[str]

    class Config:
        orm_mode = True


class WorkflowResponse(BaseModel):
    id: int
    name: str
    status: WorkflowStatusEnum
    description: Optional[str]
    steps: List[WorkflowStepResponse]

    class Config:
        orm_mode = True


class WorkflowSimplifiedResponse(BaseModel):
    id: int
    status: WorkflowStatusEnum
    name: str
    description: Optional[str]

class WorkflowSimplifiedNameResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
        from_attributes = True

class WorkflowStatusUpdateRequest(BaseModel):
    status_update: WorkflowStatusEnum