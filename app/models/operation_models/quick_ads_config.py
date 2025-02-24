from dataclasses import dataclass

@dataclass
class QuickAdsConfig:
    account_execution_id: int
    max_starting_delay: int
    requests: int
    batches: int
    batch_delay: int
    max_quick_add_pages: int = 10
    users_sent_in_request: int = 1
    argo_tokens: bool = True
