from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.schemas.subscription import SubscriptionStatus


class SubscriptionUpdateRequest(BaseModel):
    status: Optional[SubscriptionStatus] = None
    renewed_at: Optional[datetime] = None
    days_available: Optional[int] = None
    number_of_sloths: Optional[int] = None
    price: Optional[Decimal] = None
    turned_off_at: Optional[datetime] = None