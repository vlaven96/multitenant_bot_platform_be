from dataclasses import dataclass

@dataclass
class ConsumeLeadsConfig:
    account_execution_id: int
    max_starting_delay: int
    requests: int
    batches: int
    batch_delay: int
    users_sent_in_request: int = 1
    argo_tokens: bool = True
