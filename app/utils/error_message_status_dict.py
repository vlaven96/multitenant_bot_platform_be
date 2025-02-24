from app.models.account_status_enum import AccountStatusEnum
from app.models.status_enum import StatusEnum

STATUS_MAPPING_ACCOUNTS = {
    "It looks like your account may have been compromised": AccountStatusEnum.COMPROMISED_LOCKED,
    "Incorrect password, please try again": AccountStatusEnum.INCORRECT_PASSWORD,
    "Your account has been locked for violating": AccountStatusEnum.LOCKED,
    "obfuscated_phone": AccountStatusEnum.OBFUSCATED_PHONE,
    "likely failed because the account no longer exists": AccountStatusEnum.LOCKED,
    "Missing 'user_session' in login_response['bootstrap_data']": AccountStatusEnum.LOCKED,
    "Your account has been temporarily locked": AccountStatusEnum.TEMPORARY_LOCKED
}


STATUS_MAPPING_EXECUTIONS = {
    "you have reached your requests_today limit": StatusEnum.SNAPKAT_API_RATE_LIMIT_EXCEEDED,
}
