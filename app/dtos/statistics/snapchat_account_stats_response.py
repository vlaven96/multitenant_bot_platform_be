from pydantic import BaseModel
from datetime import datetime
from typing import List

class SnapchatAccountStatsDTO(BaseModel):
    total_conversations: int = 0
    chatbot_conversations: int = 0
    conversations_charged: int = 0
    cta_conversations: int = 0
    cta_shared_links: int = 0
    conversions_from_cta_links: int = 0
    total_conversions: int = 0
    quick_ads_sent: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    rejected_total: int = 0
    generated_leads: int = 0
    message: str = "Statistics retrieved successfully."
    success: bool = True

class AccountExecutionDTO(BaseModel):
    type: str
    start_time: datetime


class StatusChangeDTO(BaseModel):
    new_status: str
    changed_at: datetime


class SnapchatAccountTimelineStatisticsDTO(BaseModel):
    creation_date: datetime
    ingestion_date: datetime
    account_executions: List[AccountExecutionDTO]
    status_changes: List[StatusChangeDTO]

class ModelSnapchatAccountStatsDTO(BaseModel):
    model_name: str
    statistics: SnapchatAccountStatsDTO