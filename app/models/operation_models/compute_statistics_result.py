from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ComputeStatisticsResult:
    success: bool
    message: Optional[str] = None  # Optional message field


    def __repr__(self):
        return (
            f"ComputeStatisticsResult("
            f"message={self.message},"
            f"success={self.success})"
        )