from datetime import datetime, timedelta
from sqlalchemy.orm import Session # adjust import paths as needed

from app.dtos.subscription_create_request import SubscriptionCreateRequest
from app.dtos.subscription_response import SubscriptionResponse
from app.dtos.subscription_update_request import SubscriptionUpdateRequest
from app.schemas import Agency
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

    @staticmethod
    def get_subscription_by_agency(db: Session, agency_id: int) -> Subscription:
        """
        Retrieves the subscription associated with the provided agency_id.
        """
        return db.query(Subscription).filter(Subscription.agency_id == agency_id).first()

    @staticmethod
    def update_subscription(db: Session, agency_id: int, subscription_data: SubscriptionUpdateRequest) -> Subscription:
        """
        Updates the subscription for the provided agency_id with the given data.
        Returns the updated subscription or None if no subscription is found.
        """
        subscription = db.query(Subscription).filter(Subscription.agency_id == agency_id).first()
        if not subscription:
            return None

        # Update fields if new values are provided
        if subscription_data.status is not None:
            # Convert the incoming enum (SubscriptionStatusEnum) to the SQLAlchemy enum type if needed.
            # Here, we assume that the underlying value is stored (i.e., a string).
            subscription.status = subscription_data.status.value
        if subscription_data.renewed_at is not None:
            subscription.renewed_at = subscription_data.renewed_at
        if subscription_data.days_available is not None:
            subscription.days_available = subscription_data.days_available
        if subscription_data.number_of_sloths is not None:
            subscription.number_of_sloths = subscription_data.number_of_sloths
        if subscription_data.price is not None:
            subscription.price = subscription_data.price
        if subscription_data.turned_off_at is not None:
            subscription.turned_off_at = subscription_data.turned_off_at

        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def create_subscription(db: Session, agency_id: int, data: SubscriptionCreateRequest) -> Subscription:
        # Example logic:
        # 1) Verify the agency exists
        agency = db.query(Agency).filter(Agency.id == agency_id).first()
        if not agency:
            # handle error, or return None
            return None

        # 2) Create new Subscription model object
        renewed_at = datetime.utcnow()
        turned_off_at = renewed_at + timedelta(days=data.days_available)
        new_sub = Subscription(
            agency_id=agency_id,
            status=SubscriptionStatus.AVAILABLE,
            days_available=data.days_available,
            number_of_sloths=data.number_of_sloths,
            price=data.price,
            renewed_at=renewed_at,
            turned_off_at=turned_off_at
            # any other fields you want to set
        )

        # 3) persist in db
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)

        # 4) Return the subscription
        # If you have a Pydantic model to shape the output (SubscriptionResponse),
        # you could do something like:
        return new_sub

    @staticmethod
    def check_and_update_subscription_status(db: Session, agency_id: int) -> bool:
        """
        Checks whether the subscription for the given agency_id is still available.
        If the subscription has expired (i.e. current time is after turned_off_at), updates its status to EXPIRED.
        Returns True if the subscription is still available, otherwise False.
        """
        subscription = db.query(Subscription).filter(Subscription.agency_id == agency_id).first()
        if not subscription:
            raise ValueError(f"No subscription found for agency_id {agency_id}")

        if subscription.turned_off_at and subscription.turned_off_at < datetime.utcnow():
            if subscription.status != SubscriptionStatus.EXPIRED.value:
                subscription.status = SubscriptionStatus.EXPIRED.value
                db.commit()
            return False
        return True

    @staticmethod
    def renew_subscription(db: Session, agency_id: int, renew_data: SubscriptionUpdateRequest) -> SubscriptionResponse:
        sub = db.query(Subscription).filter(Subscription.agency_id == agency_id).first()
        if not sub:
            return None  # signals "not found"


        # 2) Update number_of_sloths if provided
        if renew_data.number_of_sloths is not None:
            sub.number_of_sloths = renew_data.number_of_sloths

        # 3) Update price if provided
        if renew_data.price is not None:
            sub.price = renew_data.price

        # 4) Renewed now
        sub.renewed_at = datetime.utcnow()

        # 5) turned_off_at = renewed_at + days_available (if days_available is set)
        if sub.days_available is not None:
            sub.turned_off_at = sub.renewed_at + timedelta(days=sub.days_available)
        else:
            sub.turned_off_at = None
        sub.status = SubscriptionStatus.AVAILABLE
        db.commit()
        db.refresh(sub)
        return sub
