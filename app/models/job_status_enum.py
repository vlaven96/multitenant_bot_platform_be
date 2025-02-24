from enum import Enum

class JobStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    DELETED = "DELETED"