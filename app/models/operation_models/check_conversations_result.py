from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CheckConversationsResult:
    conversations: int
    success: bool
    latest_events: List[str]
    message: Optional[str] = None  # Optional message field

    def __repr__(self):
        return (
            f"CheckConversationsResult("
            f"conversations={self.conversations}, "
            f"success={self.success}, "
            f"latest_events={self.latest_events}, "
            f"message={self.message})"
        )
