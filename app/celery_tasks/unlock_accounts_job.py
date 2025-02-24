import logging
from datetime import datetime, timedelta
from sqlalchemy import and_

from app.celery_app import celery
from app.database import SessionLocal
from app.models.account_status_enum import AccountStatusEnum
from app.schemas import SnapchatAccount, SnapchatAccountStatusLog

logger = logging.getLogger(__name__)

class UnlockAccountsTaskManager:

    @staticmethod
    @celery.task
    def unlock_accounts():
        """
        Celery task to unlock Snapchat accounts that have been temporarily locked
        for at least 20 days.

        Args:
            job_id (int): The unique identifier of the job to execute.

        Returns:
            None
        """
        try:
            with SessionLocal() as db:
                locked_accounts = (
                    db.query(SnapchatAccount)
                    .filter(SnapchatAccount.status == AccountStatusEnum.TEMPORARY_LOCKED)
                    .all()
                )

                for account in locked_accounts:
                    status_log = (
                        db.query(SnapchatAccountStatusLog)
                        .filter(
                            and_(
                                SnapchatAccountStatusLog.new_status == AccountStatusEnum.TEMPORARY_LOCKED,
                                SnapchatAccountStatusLog.snapchat_account_id == account.id
                            )
                        )
                        .order_by(SnapchatAccountStatusLog.created_at)
                        .first()
                    )

                    if status_log:
                        lock_duration = datetime.utcnow() - status_log.created_at
                        if lock_duration >= timedelta(days=20):
                            account.status = AccountStatusEnum.GOOD_STANDING
                            db.add(account)

                db.commit()

        except Exception as e:
            logger.error(f"Failure in unlocking accounts: {e}", exc_info=True)
