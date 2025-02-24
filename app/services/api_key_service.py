from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.api_key import APIKey

class APIKeyService:
    """
    A class to validate API keys.
    """

    @staticmethod
    def validate_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> str:
        """
        Validates the provided API key.

        Args:
            x_api_key (str): The API key provided in the header.
            db (Session): The database session dependency.

        Returns:
            str: The service name associated with the API key.

        Raises:
            HTTPException: If the API key is invalid or inactive.
        """
        api_key = db.query(APIKey).filter(APIKey.key == x_api_key, APIKey.is_active == True).first()

        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid or inactive API key")

        return api_key.service_name
