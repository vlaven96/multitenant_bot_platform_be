from pydantic import BaseModel
from datetime import date

class DailyAccountStatsDTO(BaseModel):
    day: date
    accounts_ran: int
    total_quick_ads_sent: int
