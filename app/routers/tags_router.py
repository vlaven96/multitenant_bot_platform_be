from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db  # Replace with your actual database dependency
from app.services.snapchat_account_service import SnapchatAccountService
from app.utils.security import get_current_user

router = APIRouter(
    prefix="/tags",
    tags=["Tags"]
)

@router.get("/", response_model=List[str])
def get_all_tags(db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    """
    Retrieve all distinct tags from Snapchat accounts.
    """
    return SnapchatAccountService.get_all_distinct_tags(db)

