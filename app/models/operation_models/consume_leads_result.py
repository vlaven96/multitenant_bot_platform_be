from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ConsumeLeadsResult:
    total_sent_requests: int
    added_users: List[str]
    success: bool
    message: Optional[str] = None  # Optional message field


    def __repr__(self):
        return (
            f"ConsumeLeadsResult("
            f"total_sent_requests={self.total_sent_requests}, "
            f"added_users={self.added_users}, "
            f"message={self.message}),"
            f"success={self.success})"
        )
