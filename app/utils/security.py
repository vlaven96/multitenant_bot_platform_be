import random
import string
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Header, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas import User
from app.utils.jwt_handler import verify_token
from app.services.api_key_service import APIKeyService

# Hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Password Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# 🔐 Generate a secure random password
def generate_random_password(length: int = 12) -> str:
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(characters) for _ in range(length))


# 🔐 Hash a password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# 🔐 Verify a password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# 🔑 Extract & verify current user from JWT
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


# 🔑 Restrict access to ADMIN or GLOBAL_ADMIN
def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["ADMIN", "GLOBAL_ADMIN"]:
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")
    return current_user


# 🔒 Ensure user is from the requested agency
def get_agency_id(
    agency_id: int = Path(..., description="Agency ID from the URL"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Ensures the user is part of the given agency.
    Allows GLOBAL_ADMIN to access all agencies.
    """
    user = db.query(User).filter(User.id == current_user["id"]).first()

    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    # ✅ Allow GLOBAL_ADMIN to access any agency
    if user.role == "GLOBAL_ADMIN":
        return agency_id

    # ❌ Block regular users/admins from accessing other agencies
    if user.agency_id != agency_id:
        raise HTTPException(status_code=403, detail="You do not belong to this agency.")

    return agency_id



# 🔑 Authenticate using either API Key or JWT Token
def authenticate_user_or_api_key(
        db: Session = Depends(get_db),
        x_api_key: Optional[str] = Header(None),  # API key in headers
        authorization: Optional[str] = Header(None)  # Authorization header for JWT
):
    """
    Authenticates using either an API key or a JWT token.
    If both are missing, denies access.
    """
    # ✅ Debugging logs
    print(f"[DEBUG] Received x-api-key: {x_api_key}")
    print(f"[DEBUG] Received Authorization: {authorization}")

    # ✅ Check API key authentication
    if x_api_key:
        service_name = APIKeyService.validate_api_key(x_api_key=x_api_key, db=db)
        if service_name:
            return {"auth_type": "api_key", "service_name": service_name}

    # ✅ Check Bearer token authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]
        user_payload = verify_token(token)
        if user_payload:
            return {"auth_type": "jwt", "user": user_payload}

    # ❌ No valid authentication method provided
    raise HTTPException(status_code=401, detail="Authentication required: provide either API key or Bearer token")
