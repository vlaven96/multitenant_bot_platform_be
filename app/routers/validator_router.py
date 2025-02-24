from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.services.snapchat_account_validator_service import SnapchatAccountValidatorService
from app.utils.security import get_current_user, authenticate_user_or_api_key

router = APIRouter(
    prefix="/validator",
    tags=["Validator API"]
)


@router.post("/validate-username/")
def validate_username(
    username: str,
    name: str,
    allow_duplicates: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(authenticate_user_or_api_key)
):
    """
    Validate a username and name.
    """
    try:
        result = SnapchatAccountValidatorService.check_username(
            username=username,
            name=name,
            allow_duplicates=allow_duplicates
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/is-english/")
def is_english(
    name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(authenticate_user_or_api_key)
):
    """
    Check if a name is in English.
    """
    try:
        result = SnapchatAccountValidatorService.is_english(name)
        return {"is_english": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bitmoji-image-url/")
def get_bitmoji_image_url(
    username: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(authenticate_user_or_api_key)
):
    """
    Retrieve the Bitmoji image URL for a username.
    """
    try:
        image_url, message = SnapchatAccountValidatorService.get_bitmoji_image_url(username)
        if image_url:
            return {"image_url": image_url}
        return {"message": "No Bitmoji image URL found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-bitmoji/")
def check_bitmoji(
    username: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(authenticate_user_or_api_key)
):
    """
    Check the validity of a Bitmoji for a given username.
    """
    try:
        result = SnapchatAccountValidatorService.check_bitmoji(username)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-usernames/")
def get_usernames(
    num_usernames: int,
    model_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(authenticate_user_or_api_key)
):
    """
    Fetch usernames from the database.
    """
    try:
        result = SnapchatAccountValidatorService.get_usernames(
            num_usernames=num_usernames,
            model_id=model_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
