from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from enum import Enum
class SubscriptionStatus(Enum):
    AVAILABLE = "AVAILABLE"
    EXPIRED = "EXPIRED"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), unique=True)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.AVAILABLE, nullable=False)
    renewed_at = Column(DateTime, default=datetime.utcnow)
    days_available = Column(Integer)
    number_of_sloths = Column(Integer)
    price = Column(Numeric(10, 2))
    turned_off_at = Column(DateTime)

    # Establish relationship back to Agency
    agency = relationship("Agency", back_populates="subscription")