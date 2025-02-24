from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.dtos.cookies_response import CookiesResponse
from app.schemas.cookies import Cookies
from app.schemas.snapchat_account import SnapchatAccount
from app.services.cookie_service import CookiesService
from app.utils.security import get_current_user, authenticate_user_or_api_key

router = APIRouter(
    prefix="/cookies",
    tags=["cookies"]
)

@router.get("/", response_model=List[CookiesResponse])
def get_all_cookies(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    creation_date_from: Optional[datetime] = Query(None, description="Filter cookies created after this date"),
    creation_date_to: Optional[datetime] = Query(None, description="Filter cookies created before this date")
):
    """
    Retrieves all cookies with optional filters.
    """
    return CookiesService.get_all_cookies(
        db=db
    )

@router.get("/{cookie_id}", response_model=CookiesResponse)
def get_cookie_by_id(
    cookie_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves a single cookie by its ID.
    """
    cookie = CookiesService.get_cookie_by_id(db, cookie_id)
    if not cookie:
        raise HTTPException(status_code=404, detail="Cookie not found.")
    return cookie

@router.post("/", response_model=CookiesResponse)
def create_cookie(
    payload: dict = Body(..., description="JSON payload to create a new cookie."),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new cookie.
    """
    try:
        return CookiesService.create_cookie(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{cookie_id}", response_model=dict)
def delete_cookie(
    cookie_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a cookie by its ID.
    """
    if not CookiesService.delete_cookie(db, cookie_id):
        raise HTTPException(status_code=404, detail="Cookie not found.")
    return {"message": "Cookie deleted successfully."}

@router.get("/snapchat-account/{username}", response_model=CookiesResponse)
def get_cookie_for_snapchat_account(
    username: str,
    db: Session = Depends(get_db),
    auth: str = Depends(authenticate_user_or_api_key),
    x_api_key: Optional[str] = Header(None),
):
    """
    Retrieves a cookie associated with a specific Snapchat account username.
    """
    account = db.query(SnapchatAccount).filter(SnapchatAccount.username == username).first()
    if not account or not account.cookies:
        raise HTTPException(status_code=404, detail="No cookie found for the given username.")
    return account.cookies