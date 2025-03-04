import re
class UserFriendlyMessageUtils:
    @staticmethod
    def get_user_friendly_message(raw_message: str) -> str:
        """
        Transforms a raw internal message into a simplified, user-friendly version.
        Checks if specific substrings are present in the message and returns a complete replacement if found.
        """
        # First, remove any internal worker tags
        message = re.sub(r"\[Worker-\d+\]\s*", "", raw_message)

        # Mapping of substrings to replacement messages
        replacements = {
            "An error occurred during login (attempt 3): timed out": "Login failed due to proxy issues.",
            "Error connecting to GMX email": "Unable to retrieve the ODLV code due to invalid email credentials or the code not being sent.",
            "Your account has been locked": "Your account has been locked.",
            "Missing expected key in login response": "Login failed, possibly due to a locked account.",
            "Maximum retry attempts reached: Failed to decode Argos Protobuf response": "Login failed due to proxy issues or a locked account.",
            "you have reached your requests_today limit, please upgrade your subscription or wait in order to use the API": "Request limit reached. Please contact the platform administrator for assistance.",
            "Finished processing quick adds": "Quick add processing completed.",
            "Reached the maximum of": "Quick add processing completed."
        }

        # Check each key; if it is found, return its corresponding replacement message
        for key, replacement in replacements.items():
            if key in message:
                return replacement

        # If none of the key phrases match, remove any debug details if present
        if "Debug message:" in message:
            message = message.split("Debug message:")[0].strip()

        return message