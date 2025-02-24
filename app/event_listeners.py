from sqlalchemy.event import listens_for
from datetime import datetime
from sqlalchemy.orm.attributes import get_history

from app.models.account_status_enum import AccountStatusEnum
from app.schemas.snapchat_account import SnapchatAccount
from app.schemas.snapchat_account_status_log import SnapchatAccountStatusLog

def to_enum_if_str(value):
    if isinstance(value, str):
        return AccountStatusEnum(value)
    return value

@listens_for(SnapchatAccount, 'before_update')
def log_status_change(mapper, connection, target):
    """Logs status changes for SnapchatAccount objects."""
    # Retrieve the old and new values for the 'status' attribute
    print("Attempting to change the status")
    history = get_history(target, 'status')
    if history.has_changes():
        old_status = history.deleted[0] if history.deleted else None
        new_status = history.added[0] if history.added else None

        if old_status:
            old_status_enum = to_enum_if_str(old_status)
        else:
            old_status_enum = None
        new_status_enum = to_enum_if_str(new_status)

        if old_status_enum != new_status_enum and (
                old_status_enum is None or old_status_enum.value != new_status_enum.value
        ):
            connection.execute(
                SnapchatAccountStatusLog.__table__.insert(),
                {
                    'snapchat_account_id': target.id,
                    'old_status': old_status_enum,
                    'new_status': new_status_enum,
                    'changed_at': datetime.utcnow()
                }
            )
