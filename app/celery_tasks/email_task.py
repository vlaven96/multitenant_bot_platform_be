from app.celery_app import celery
from fastapi_mail import MessageSchema, FastMail
import asyncio

import logging
from app.config import settings, email_settings

logger = logging.getLogger(__name__)
class EmailTaskManager:
    @staticmethod
    @celery.task
    def send_email_task(recipient: str, agency_name: str, registration_link: str):
        logger.info(f"[CELERY] Send email execution started with recipient {recipient}.")
        message = MessageSchema(
            subject="Complete Your Registration",
            recipients=[recipient],
            body=(
                f"Hello,\n\n"
                f"You have been invited to join the '{agency_name}' agency. "
                f"To complete your registration, please click the link below:\n{registration_link}\n\n"
                "If you did not request this invitation, please ignore this email."
            ),

            subtype="plain"
        )
        fm = FastMail(email_settings.mail_config)
        # Use the synchronous send_message method
        try:
            # Run the async send_message in a synchronous context.
            asyncio.run(fm.send_message(message))
            logger.info(f"[CELERY] Email was sent to recipient {recipient}.")
        except Exception as e:
            logger.error(f"[CELERY] Failed to send email: {e}")

    @staticmethod
    @celery.task
    def send_email_create_agency_task(recipient: str, registration_link: str):
        logger.info(f"[CELERY] Send email execution started with recipient {recipient}.")
        message = MessageSchema(
            subject="Complete Your Agency Registration",
            recipients=[recipient],
            body=(
                f"Hello,\n\nYour were invited to create a new agency.\n"
                f"Please complete the registration by clicking the link below:\n{registration_link}\n\n"
                "If you did not request this, please ignore this email."
            ),
            subtype="plain"
        )
        fm = FastMail(email_settings.mail_config)
        # Use the synchronous send_message method
        try:
            # Run the async send_message in a synchronous context.
            asyncio.run(fm.send_message(message))
            logger.info(f"[CELERY] Email was sent to recipient {recipient}.")
        except Exception as e:
            logger.error(f"[CELERY] Failed to send email: {e}")