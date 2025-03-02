from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.dtos.subscription_create_request import SubscriptionCreateRequest
from app.dtos.subscription_response import SubscriptionResponse
from app.dtos.subscription_update_request import SubscriptionUpdateRequest
from app.services.subscription_service import SubscriptionService  # adjust import as needed
from app.utils.security import get_agency_id, get_global_admin

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)

@router.get("/", response_model=SubscriptionResponse)
def get_subscription(
    agency_id: int = Depends(get_agency_id),
    db: Session = Depends(get_db)
):
    """
    Retrieve the subscription details for a given agency.
    """
    subscription = SubscriptionService.get_subscription_by_agency(db, agency_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found for this agency")
    return subscription


@router.post("/", response_model=SubscriptionResponse)
def create_subscription(
        subscription_data: SubscriptionCreateRequest,
        agency_id: int = Depends(get_agency_id),
        admin: dict = Depends(get_global_admin),  # if you want only global_admins
        db: Session = Depends(get_db)
):
    """
    Create a subscription for the given agency.
    """
    # You might first check if the agency already has a subscription
    existing_subscription = SubscriptionService.get_subscription_by_agency(db, agency_id)
    if existing_subscription:
        raise HTTPException(status_code=400, detail="Subscription already exists for this agency.")

    new_subscription = SubscriptionService.create_subscription(db, agency_id, subscription_data)
    if not new_subscription:
        # if service returned None for some reason
        raise HTTPException(status_code=500, detail="Failed to create subscription.")

    return new_subscription

@router.put("/", response_model=SubscriptionResponse)
def update_subscription(
    agency_id: int = Depends(get_agency_id),
    admin: dict = Depends(get_global_admin),
    subscription_data: SubscriptionUpdateRequest = ...,
    db: Session = Depends(get_db)
):
    """
    Update the subscription details for a given agency.
    The update logic is handled in the service layer.
    """
    updated_subscription = SubscriptionService.update_subscription(db, agency_id, subscription_data)
    if not updated_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found for this agency")
    return updated_subscription

@router.put("/renew", response_model=SubscriptionResponse)
def renew_subscription(
    renew_data: SubscriptionUpdateRequest,
    agency_id: int = Depends(get_agency_id),
    admin: dict = Depends(get_global_admin),
    db: Session = Depends(get_db)
):
    """
    Renew the subscription for a given agency.
    - Sets a new `renewed_at` to now.
    - Recalculates `turned_off_at` = `renewed_at + days_available`.
    - Optionally updates days_available or other fields if provided.
    """
    renewed_sub = SubscriptionService.renew_subscription(db, agency_id, renew_data)
    if not renewed_sub:
        raise HTTPException(status_code=404, detail="Subscription not found for this agency.")
    return renewed_sub