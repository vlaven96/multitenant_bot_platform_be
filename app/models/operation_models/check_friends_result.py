from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CheckFriendsResult:
    sent_requests: int
    accepted_friend_requests: int
    friends: List[str]
    added_users: List[str]
    success: bool
    message: Optional[str] = None  # Optional message field


    def __repr__(self):
        return (
            f"CheckFriendsResult("
            f"sent_requests={self.sent_requests}, "
            f"accepted_friend_requests={self.accepted_friend_requests}, "
            f"friends={self.friends}, "
            f"added_users={self.added_users}, "
            f"success={self.success}, "
            f"message={self.message})"
        )
