# app/config.py
import os
from dotenv import load_dotenv

from app.services.key_vault.key_vault_manager import KeyVaultManager
from pydantic_settings import BaseSettings

from fastapi_mail import ConnectionConfig
load_dotenv()

if not os.getenv("SNAPKAT_API_KEY"):
    print("Fetching SNAPKAT_API_KEY from Key Vault...")  # Debug log
    os.environ["SNAPKAT_API_KEY"] = KeyVaultManager.get_secret("SNAPKAT_API_KEY")

SNAPKAT_API_KEY = os.getenv("SNAPKAT_API_KEY")


class Settings:
    ENV: str = os.getenv("ENV", "development")  # Default to "development"
    FRONTEND_URL_LOCAL: str = os.getenv("FRONTEND_URL_LOCAL", "http://localhost:3000")
    FRONTEND_URL_PROD: str = os.getenv("FRONTEND_URL_PROD", "https://snepflow.com")

    @property
    def frontend_url(self) -> str:
        """Dynamically select the correct frontend URL"""
        return self.FRONTEND_URL_LOCAL if self.ENV == "development" else self.FRONTEND_URL_PROD


class EmailSettings(BaseSettings):
    SECRET_KEY: str = "f3a7d8b4c5e9d0123456789abcdef0123456789abcdef0123456789abcdef01"  # Use a secure key in production
    ALGORITHM: str = "HS256"

    # GMX SMTP Credentials
    MAIL_USERNAME: str = "snepflow@gmx.com"  # Your GMX email
    MAIL_PASSWORD: str = "WZ4*WbEn7687?bt"  # Your GMX email password
    MAIL_FROM: str = "snepflow@gmx.com"  # Sender email
    MAIL_PORT: int = 587  # GMX uses port 587 for TLS
    MAIL_SERVER: str = "mail.gmx.com"
    MAIL_STARTTLS: bool = True  # Use STARTTLS for secure connection
    MAIL_SSL_TLS: bool = False  # Don't use SSL/TLS directly
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    @property
    def mail_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            MAIL_USERNAME=self.MAIL_USERNAME,
            MAIL_PASSWORD=self.MAIL_PASSWORD,
            MAIL_FROM=self.MAIL_FROM,
            MAIL_PORT=self.MAIL_PORT,
            MAIL_SERVER=self.MAIL_SERVER,
            MAIL_STARTTLS=self.MAIL_STARTTLS,
            MAIL_SSL_TLS=self.MAIL_SSL_TLS,
            USE_CREDENTIALS=self.USE_CREDENTIALS,
            VALIDATE_CERTS=self.VALIDATE_CERTS,
        )


email_settings = EmailSettings()
settings = Settings()
