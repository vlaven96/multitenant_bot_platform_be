from datetime import datetime

from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.cookies import Cookies
from app.schemas.snapchat_account import SnapchatAccount


class CookiesService:

    @staticmethod
    def get_all_cookies(
        db: Session,
    ) -> List[Cookies]:
        """
        Retrieves all cookies with optional filters.
        """
        query = db.query(Cookies)
        return query.all()

    @staticmethod
    def get_cookie_by_id(db: Session, cookie_id: int) -> Optional[Cookies]:
        """
        Retrieves a single cookie by its ID.
        """
        return db.query(Cookies).filter(Cookies.id == cookie_id).first()

    @staticmethod
    def get_cookie_for_snapchat_account(db: Session, username: str) -> Optional[Cookies]:
        """
        Retrieves the cookie associated with a specific Snapchat account username.
        """
        account = db.query(SnapchatAccount).filter(SnapchatAccount.username == username).first()
        if not account or not account.cookies:
            return None
        return account.cookies

    @staticmethod
    def create_cookie(db: Session, payload: dict) -> Cookies:
        """
        Creates a new cookie.
        """
        cookie = Cookies(**payload)
        db.add(cookie)
        db.commit()
        db.refresh(cookie)
        return cookie

    @staticmethod
    def delete_cookie(db: Session, cookie_id: int) -> bool:
        """
        Deletes a cookie by its ID.
        """
        cookie = db.query(Cookies).filter(Cookies.id == cookie_id).first()
        if not cookie:
            return False

        db.delete(cookie)
        db.commit()
        return True
