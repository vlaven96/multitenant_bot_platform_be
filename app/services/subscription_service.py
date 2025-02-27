from datetime import datetime
from sqlalchemy.orm import Session # adjust import paths as needed

from app.schemas.subscription import Subscription, SubscriptionStatus


class SubscriptionService:
    @staticmethod
    def is_subscription_available(db: Session, agency_id: int) -> bool:
        """
        Check if the subscription for the given agency_id is still available.
        If the subscription's turned_off_at is in the past, update its status to EXPIRED and return False.
        Otherwise, return True.

        Args:
            db (Session): SQLAlchemy session.
            agency_id (int): The agency identifier.

        Returns:
            bool: True if the subscription is still available; False if it has expired.

        Raises:
            ValueError: If no subscription exists for the given agency.
        """
        subscription = db.query(Subscription).filter(Subscription.agency_id == agency_id).first()
        if subscription is None:
            raise ValueError(f"No subscription found for agency_id {agency_id}")
        if Subscription.status ==SubscriptionStatus.EXPIRED:
            return False
        # Check if the subscription has expired.
        if subscription.turned_off_at and subscription.turned_off_at < datetime.utcnow():
            if subscription.status != SubscriptionStatus.EXPIRED:
                subscription.status = SubscriptionStatus.EXPIRED
                db.commit()
            return False

        return True

