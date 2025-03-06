from app.schemas.user import UserRole, User
from app.utils.security import hash_password
from sqlalchemy.orm import Session

class UserService:
    @staticmethod
    def create_user_admin(db: Session, agency_id: int, email: str, username: str, password: str):
        role_enum = UserRole.ADMIN

        # Create the new user
        new_user = User(
            username=username,
            email=email,
            password=hash_password(password),
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