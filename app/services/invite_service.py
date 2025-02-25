import jwt
from datetime import datetime, timedelta

from app.config import settings


class InviteService:
    @staticmethod
    def generate_user_invite_token(agency_id: int, email: str, role: str) -> str:
        payload = {
            "agency_id": agency_id,
            "invite_email": email,
            "role": role,  # e.g., "user" or other role
            "exp": datetime.utcnow() + timedelta(hours=24),
            "type": "user_invite"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token
