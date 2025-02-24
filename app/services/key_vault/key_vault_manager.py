import requests
import configparser
import os

class KeyVaultManager:
    BASE_AUTH_URL = "https://auth.idp.hashicorp.com/oauth2/token"
    BASE_SECRETS_URL = "https://api.cloud.hashicorp.com/secrets/2023-11-28"
    CONFIG = None

    @staticmethod
    def load_config(config_file: str = "config.ini"):
        """
        Loads configuration from a file and stores it in a class-level attribute.
        """
        if KeyVaultManager.CONFIG is None:  # Load only once
            current_dir = os.path.dirname(__file__)  # Directory of the current script
            config_path = os.path.join(current_dir, config_file)
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            config = configparser.ConfigParser()
            config.read(config_path)
            KeyVaultManager.CONFIG = {
                "CLIENT_ID": config.get("credentials", "CLIENT_ID"),
                "CLIENT_SECRET": config.get("credentials", "CLIENT_SECRET"),
                "ORGANIZATION_ID": config.get("settings", "ORGANIZATION_ID"),
                "PROJECT_ID": config.get("settings", "PROJECT_ID"),
                "APP_NAME": config.get("settings", "APP_NAME"),
            }

    @staticmethod
    def get_access_token() -> str:
        """
        Retrieves an OAuth2 access token using the provided client credentials.
        """
        KeyVaultManager.load_config()  # Ensure config is loaded
        auth_payload = {
            "client_id": KeyVaultManager.CONFIG["CLIENT_ID"],
            "client_secret": KeyVaultManager.CONFIG["CLIENT_SECRET"],
            "grant_type": "client_credentials",
            "audience": "https://api.hashicorp.cloud"
        }
        auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(KeyVaultManager.BASE_AUTH_URL, data=auth_payload, headers=auth_headers)
        response.raise_for_status()
        return response.json().get("access_token")

    @staticmethod
    def get_all_secrets() -> list:
        """
        Retrieves a list of all secret names for the specified application.
        """
        KeyVaultManager.load_config()  # Ensure config is loaded
        token = KeyVaultManager.get_access_token()
        secrets_url = f"{KeyVaultManager.BASE_SECRETS_URL}/organizations/{KeyVaultManager.CONFIG['ORGANIZATION_ID']}/projects/{KeyVaultManager.CONFIG['PROJECT_ID']}/apps/{KeyVaultManager.CONFIG['APP_NAME']}/secrets:open"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(secrets_url, headers=headers)
        response.raise_for_status()

        secrets = response.json().get("secrets", [])
        return [secret.get("name") for secret in secrets]

    @staticmethod
    def get_secret(secret_name: str) -> str:
        """
        Retrieves the value of a specific secret by its name directly via API.
        """
        KeyVaultManager.load_config()  # Ensure config is loaded
        token = KeyVaultManager.get_access_token()
        secret_url = f"{KeyVaultManager.BASE_SECRETS_URL}/organizations/{KeyVaultManager.CONFIG['ORGANIZATION_ID']}/projects/{KeyVaultManager.CONFIG['PROJECT_ID']}/apps/{KeyVaultManager.CONFIG['APP_NAME']}/secrets/{secret_name}:open"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(secret_url, headers=headers)
        response.raise_for_status()

        # Extract and return the secret value
        secret_value = response.json().get("secret", {}).get("static_version", {}).get("value", None)
        if not secret_value:
            raise ValueError(f"Secret '{secret_name}' not found or has no value.")
        return secret_value

