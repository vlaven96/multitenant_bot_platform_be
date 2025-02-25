from sqlalchemy.orm import Session
from typing import List, Dict

from app.models.account_status_enum import AccountStatusEnum
from app.schemas.proxy import Proxy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.schemas.snapchat_account import SnapchatAccount


class ProxyService:
    @staticmethod
    def get_all_proxies(db: Session, agency_id: int) -> List[Proxy]:
        """
        Retrieves all proxies from the database that belong to the specified agency.
        """
        return db.query(Proxy).filter(Proxy.agency_id == agency_id).all()

    @staticmethod
    def get_proxy_by_id(db: Session, proxy_id: int) -> Proxy:
        """
        Retrieves a specific proxy by its ID.
        """
        return db.query(Proxy).filter(Proxy.id == proxy_id).first()

    @staticmethod
    def create_proxies(db: Session, agency_id:int, payload: Dict[str, List[Dict[str, str]]]) -> List[Proxy]:
        """
        Creates new proxies from a JSON payload.
        """
        proxies_data = payload.get("data")
        if not proxies_data or not isinstance(proxies_data, str):
            raise ValueError("Invalid payload. 'data' field must be a string.")

        created_proxies = []
        errors = []

        for index, proxy_data in enumerate(proxies_data.splitlines()):
            try:
                fields = proxy_data.strip().split(":")
                if len(fields) != 4:
                    raise ValueError(f"Invalid format on line {index + 1}: {proxy_data}")
                host = fields[0].strip()
                port = fields[1].strip()
                proxy_username = fields[2].strip()
                proxy_password = fields[3].strip()

                if not proxy_username or not proxy_password or not host:
                    raise ValueError(f"Missing required fields for proxy at index {index + 1}.")

                # Create Proxy object
                proxy = Proxy(
                    proxy_username=proxy_username,
                    proxy_password=proxy_password,
                    host=host,
                    port=port,
                    agency_id=agency_id
                )
                db.add(proxy)
                created_proxies.append(proxy)

            except Exception as e:
                errors.append(f"Error processing proxy at index {index + 1}: {str(e)}")
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Database integrity error: {str(e.orig)}")

        if errors:
            raise ValueError(f"Some proxies could not be processed: {errors}")

        return created_proxies

    @staticmethod
    def delete_proxy(db: Session, proxy_id: int):
        proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if proxy:
            db.delete(proxy)
            db.commit()

        proxies = (
            db.query(Proxy, func.count(SnapchatAccount.id).label("account_count"))
                .outerjoin(SnapchatAccount, Proxy.id == SnapchatAccount.proxy_id)
                .group_by(Proxy.id)
                .order_by(func.count(SnapchatAccount.id).asc())  # Sort by least usage
                .all()
        )

        if not proxies:
            print("No proxies available in the system.")
            return True
        proxy_usage = {proxy.id: count for proxy, count in proxies}
        proxy_pool = list(proxy_usage.keys())

        accounts_with_no_proxy = (
            db.query(SnapchatAccount)
                .filter(
                (SnapchatAccount.proxy_id == None) &
                (SnapchatAccount.status.in_([AccountStatusEnum.RECENTLY_INGESTED,
                                             AccountStatusEnum.GOOD_STANDING,
                                             AccountStatusEnum.CAPTCHA]))
            )
                .all()
        )

        for account in accounts_with_no_proxy:
            if not proxy_pool:
                raise ValueError("No proxies available to reassign.")

            assigned_proxy_id = proxy_pool[0]
            account.proxy_id = assigned_proxy_id
            proxy_usage[assigned_proxy_id] += 1
            proxy_pool = sorted(proxy_pool, key=lambda proxy_id: proxy_usage[proxy_id])

        db.commit()
        return True

    @staticmethod
    def get_least_used_proxy(db: Session, agency_id:int, max_associations: int = None):
        """
        Retrieves the proxy with the least number of SnapchatAccount associations.
        Optionally filters proxies by a maximum number of associations.

        Args:
            db (Session): Database session.
            max_associations (int): Maximum number of allowed associations.

        Returns:
            Proxy: The proxy object with the least associations or None.
        """
        # Query proxies with their association count
        proxy_with_counts = (
            db.query(Proxy, func.count(SnapchatAccount.id).label("association_count"))
                .filter(Proxy.agency_id == agency_id)
                .outerjoin(SnapchatAccount, Proxy.id == SnapchatAccount.proxy_id)
                .group_by(Proxy.id)
                .order_by(func.count(SnapchatAccount.id).asc())  # Sort by least associations
        )

        # If max_associations is provided, filter proxies with associations within the limit
        if max_associations is not None:
            proxy_with_counts = proxy_with_counts.having(func.count(SnapchatAccount.id) <= max_associations)

        # Retrieve the first proxy that matches the criteria
        result = proxy_with_counts.first()
        return result[0] if result else None