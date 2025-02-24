from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DPARequestParams:
    client: object
    quick_ads_page: int
    sent_requests_quick_ads: int
    added_usernames: List[str]
    message: Optional[str]
    max_friend_requests: int
    users_send_in_request: int
    rejected_count: int
