import secrets


class APIKeyUtils:
    """
    A class to generate secure random API keys.
    """

    @staticmethod
    def generate_api_key() -> str:
        """
        Generates a secure random API key.

        Returns:
            str: A secure random API key.
        """
        return secrets.token_urlsafe(32)

