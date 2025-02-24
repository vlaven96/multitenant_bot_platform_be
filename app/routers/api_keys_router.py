from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dtos.create_api_key_request import CreateAPIKeyRequest
from app.schemas.api_key import APIKey
from app.utils.api_key_utils import APIKeyUtils
from app.utils.security import get_admin_user

router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"]
)
@router.post("/")
def create_api_key(request: CreateAPIKeyRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """
    Creates a new API key for a given service. Only admins can perform this action.
    """
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can create API keys.")

    new_key = APIKeyUtils.generate_api_key()
    api_key = APIKey(key=new_key, service_name=request.service_name, is_active=True)

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {"api_key": api_key.key, "service_name": api_key.service_name}

@router.get("/")
def list_api_keys(db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """
    Lists all API keys. Only admins can access this information.
    """
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can list API keys.")

    api_keys = db.query(APIKey).all()
    return api_keys

@router.delete("/{key_id}")
def deactivate_api_key(key_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    """
    Deactivates an API key by its ID. Only admins can perform this action.
    """
    if not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can deactivate API keys.")

    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
    return {"message": "API key deactivated successfully"}