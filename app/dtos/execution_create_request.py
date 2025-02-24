from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ExecutionCreateRequest(BaseModel):
    type: str
    configuration: Dict[str, Any]
    accounts: Optional[List[int]]