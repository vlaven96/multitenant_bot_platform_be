# app/config.py
import os
from app.services.key_vault.key_vault_manager import KeyVaultManager

if not os.getenv("SNAPKAT_API_KEY"):
    print("Fetching SNAPKAT_API_KEY from Key Vault...")  # Debug log
    os.environ["SNAPKAT_API_KEY"] = KeyVaultManager.get_secret("SNAPKAT_API_KEY")

SNAPKAT_API_KEY = os.getenv("SNAPKAT_API_KEY")
