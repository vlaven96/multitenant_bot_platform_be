from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.schemas.subscription import SubscriptionStatus


class SubscriptionResponse(BaseModel):
    id: int
    agency_id: int
    status: SubscriptionStatus
    renewed_at: datetime
    days_available: int
    number_of_sloths: int
    price: Decimal
    turned_off_at: Optional[datetime] = None

    class Config:
        orm_mode = True