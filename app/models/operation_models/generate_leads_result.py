from typing import List, Optional
from dataclasses import dataclass

@dataclass
class GenerateLeadsResult:
    generated_leads: int
    rejected_count: int
    quick_add_pages_requested: int
    added_users: List[str]
    success: bool
    message: Optional[str] = None


    def __repr__(self):
        return (
            f"GenerateLeadsResult("
            f"generated_leads={self.generated_leads}, "
            f"rejected_count={self.rejected_count}, "
            f"quick_add_pages_requested={self.quick_add_pages_requested}, "
            f"added_users={self.added_users}, "
            f"message={self.message}),"
            f"success={self.success})"
        )
