import jwt

from app.schemas import User
from app.schemas.user import UserRole
from app.utils.security import hash_password
from app.config import settings


class AuthService:
    @staticmethod
    def complete_admin_registration(db, token: str, username: str, password: str) -> User:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "admin_invite":
                raise ValueError("Invalid token type")
            agency_id = payload.get("agency_id")
            admin_email = payload.get("admin_email")
            role_str = payload.get("role", "admin")
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.PyJWTError:
            raise ValueError("Invalid token")

        # Check if a user with this email already exists
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            raise ValueError("User already registered with this email")

        role_enum = UserRole.ADMIN if role_str.lower() == "admin" else UserRole.USER

        new_user = User(
            username=username,
            email=admin_email,
            password=hash_password(password),
            role=role_enum,
            agency_id=agency_id
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def complete_user_registration(db, token: str, username: str, password: str) -> User:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "user_invite":
                raise ValueError("Invalid token type")
            agency_id = payload.get("agency_id")
            invite_email = payload.get("invite_email")
            role_str = payload.get("role", "user")
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.PyJWTError:
            raise ValueError("Invalid token")

        existing_user = db.query(User).filter(User.email == invite_email).first()
        if existing_user:
            raise ValueError("User already registered with this email")

        role_enum = UserRole.ADMIN if role_str.lower() == "admin" else UserRole.USER

        new_user = User(
            username=username,
            email=invite_email,
            password=hash_password(password),
            role=role_enum,
            agency_id=agency_id
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
