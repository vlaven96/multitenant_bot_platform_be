from pydantic import BaseModel
from typing import Optional

from app.schemas.subscription import SubscriptionStatus


class SubscriptionCreateRequest(BaseModel):
    # Include the subscription fields you need to create
    days_available: int
    number_of_sloths: int
    price: float
    # any other fields you want to create
