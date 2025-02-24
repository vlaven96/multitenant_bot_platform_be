from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CheckStatusResult:
    success: bool
    message: Optional[str] = None  # Optional message field


    def __repr__(self):
        return (
            f"CheckStatusResult("
            f"message={self.message},"
            f"success={self.success})"
        )