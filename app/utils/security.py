from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.services.api_key_service import APIKeyService
from app.utils.jwt_handler import verify_token
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends, HTTPException, Header
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

def get_admin_user(current_user: dict = Depends(get_current_user)):
    # Check if the current user is an admin
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")
    return current_user

def authenticate_user_or_api_key(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),  # API key in headers
    authorization: Optional[str] = Header(None)  # Authorization header for JWT
):
    """
    Authenticates using either an API key or a JWT token.
    """
    # Debugging
    print(f"Received x-api-key: {x_api_key}")
    print(f"Received Authorization: {authorization}")

    # Check API key first
    if x_api_key:
        service_name = APIKeyService.validate_api_key(x_api_key=x_api_key, db=db)
        return {"auth_type": "api_key", "service_name": service_name}

    # Check Authorization header (JWT)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]
        user_payload = verify_token(token)
        if not user_payload:
            raise HTTPException(status_code=401, detail="Invalid or expired JWT token")
        return {"auth_type": "jwt", "user": user_payload}

    # No valid authentication provided
    raise HTTPException(status_code=401, detail="Authentication required: provide either API key or Bearer token")