from app.celery_app import celery
from fastapi_mail import MessageSchema, FastMail
import asyncio

import logging
from app.config import settings

logger = logging.getLogger(__name__)
class EmailTaskManager:
    @staticmethod
    @celery.task
    def send_email_task(recipient: str, agency_name: str, registration_link: str):
        logger.info(f"[CELERY] Send email execution started with recipient {recipient}.")
        message = MessageSchema(
            subject="Complete Your Admin Registration",
            recipients=[recipient],
            body=(
                f"Hello,\n\nYour agency '{agency_name}' has been registered successfully.\n"
                f"Please complete your admin registration by clicking the link below:\n{registration_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            subtype="plain"
        )
        fm = FastMail(settings.mail_config)
        # Use the synchronous send_message method
        try:
            # Run the async send_message in a synchronous context.
            asyncio.run(fm.send_message(message))
            logger.info(f"[CELERY] Email was sent to recipient {recipient}.")
        except Exception as e:
            logger.error(f"[CELERY] Failed to send email: {e}")