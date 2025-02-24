from enum import Enum as PyEnum


class WorkflowStepTypeEnum(PyEnum):
    CHANGE_STATUS = "CHANGE_STATUS"
    ADD_TAG = "ADD_TAG"
    REMOVE_TAG = "REMOVE_TAG"
