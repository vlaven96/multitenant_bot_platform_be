import jwt
from sqlalchemy.orm import Session
from app.dtos.user_create_request import UserCreateRequest
from app.schemas import User
from app.schemas.user import UserRole
from app.utils.security import hash_password
from app.config import settings, email_settings


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
    def complete_registration(db: Session, user_data: UserCreateRequest) -> dict:
        """
        Validates the registration token, extracts user details, and creates the user.
        """
        try:
            # Decode the JWT token
            payload = jwt.decode(user_data.token, email_settings.SECRET_KEY, algorithms=[email_settings.ALGORITHM])

            # Validate token type
            if payload.get("type") != "user_invitation":
                raise ValueError("Invalid token type")

            # Extract data from token
            agency_id = payload["agency_id"]
            email = payload["email"]
            role_str = payload["role"].upper()  # Normalize role

        except jwt.ExpiredSignatureError:
            raise ValueError("Invitation token expired")
        except jwt.PyJWTError:
            raise ValueError("Invalid token")

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User already registered")

        # Validate role
        if role_str not in ["ADMIN", "USER"]:
            raise ValueError("Invalid role in token")

        role_enum = UserRole.ADMIN if role_str == "ADMIN" else UserRole.USER

        # Create the new user
        new_user = User(
            username=user_data.username,
            email=email,
            password=hash_password(user_data.password),
            role=role_enum,
            agency_id=agency_id  # Assign user to the correct agencya
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User registered successfully",
            "role": role_enum.name,
            "agency_id": agency_id
        }
