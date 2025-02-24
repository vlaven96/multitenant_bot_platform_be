from datetime import datetime
import re
from typing import Dict


class SnapchatAccountUtils:
    @staticmethod
    def parse_creation_date(creation_date_str: str, index: int) -> datetime:
        """
        Parses the creation date string. Supports full date (%Y-%m-%d) or only the year (%Y).
        Defaults to January 1st if only the year is provided.

        :param creation_date_str: The creation date string.
        :param index: The index of the line being processed, used for error reporting.
        :return: A datetime object representing the creation date.
        """
        try:
            # Try parsing as full date
            return datetime.strptime(creation_date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try parsing as year only, default to January 1st
                return datetime.strptime(creation_date_str, "%Y").replace(month=1, day=1)
            except ValueError:
                raise ValueError(f"Invalid date format on line {index + 1}: {creation_date_str}")

    @staticmethod
    def _sanitize_placeholder_name(name: str) -> str:
        """
        Converts an arbitrary placeholder name (e.g., '2fa') into a valid Python
        identifier for use in named groups (e.g., '_2fa'). We'll map it back later.
        """
        # If it doesn't start with a letter or underscore, prepend underscore
        if not re.match(r"[a-zA-Z_]", name):
            name = f"_{name}"
        # Replace any invalid characters (anything not alphanumeric or underscore)
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return name

    @staticmethod
    def parse_account_linev2(line: str, index: int, pattern: str) -> Dict[str, str]:
        """
        Parses a single line of input based on a given pattern with customizable separators.

        Example placeholders:
          - {username}, {password}, {2fa}, {creation_date}, ...
        Example separators:
          - [spaces] -> one or more whitespace
          - [:]      -> optional spaces around a colon
          (Extend as needed.)

        The logic ensures only the *last* placeholder can capture multiple words
        (if needed). Intermediate placeholders each capture a single token (no spaces).
        """
        # Map special placeholders to their regex equivalents
        SEPARATOR_MAP = {
            "[spaces]": r"\s+",
            "[:]": r"\s*:\s*",
        }

        # Step 1: Tokenize the pattern so we can build the regex piece by piece
        # We'll split on either a {placeholder} or a [something].
        # This retains those tokens in the result so we can handle them specifically.
        tokens = re.split(r"(\{.*?\}|\[.*?\])", pattern)

        # Filter out empty tokens from splitting
        tokens = [t for t in tokens if t]

        # Identify all placeholders of the form {something}
        placeholders = [t for t in tokens if t.startswith("{") and t.endswith("}")]
        num_placeholders = len(placeholders)

        # We'll build the final regex in parts
        regex_parts = []
        placeholder_index = 0  # which placeholder # we are on

        # Helper to see if we are on the last placeholder
        def is_last_placeholder():
            return placeholder_index == num_placeholders - 1

        # A map from sanitized group name -> original placeholder (e.g., '_2fa' -> '2fa')
        group_name_map = {}

        for token in tokens:
            # Is it a separator like [spaces] or [:]?
            if token.startswith("[") and token.endswith("]"):
                # Convert e.g. [spaces] to \s+ or [:] to \s*:\s*
                if token in SEPARATOR_MAP:
                    regex_parts.append(SEPARATOR_MAP[token])
                else:
                    # If we have an unknown custom separator, escape it or handle it differently
                    # For safety, treat it as a literal bracket sequence
                    regex_parts.append(re.escape(token))
            # Is it a placeholder like {username}?
            elif token.startswith("{") and token.endswith("}"):
                raw_name = token[1:-1]  # e.g. 'username' from '{username}'
                sanitized_name = SnapchatAccountUtils._sanitize_placeholder_name(raw_name)
                group_name_map[sanitized_name] = raw_name

                # If this is the last placeholder, allow multi-word capture (greedy):
                if is_last_placeholder():
                    # e.g. (?P<placeholder>.+)
                    part = f"(?P<{sanitized_name}>.+)"
                else:
                    # otherwise capture a single token up to next whitespace: (?P<placeholder>[^\\s]+)
                    part = f"(?P<{sanitized_name}>[^\\s]+)"

                regex_parts.append(part)
                placeholder_index += 1
            else:
                # Regular text in the pattern, just escape it
                # (In your usage, you might not have literal text, but let's be safe.)
                regex_parts.append(re.escape(token))

        # Build the final regex, anchored
        final_regex = "^" + "".join(regex_parts) + "$"

        # Step 2: Match against the input line
        match = re.match(final_regex, line.strip())
        if not match:
            raise ValueError(f"Invalid format on line {index + 1}: {line}")

        # Step 3: Retrieve the groups, mapping sanitized names back to original
        captured = {}
        for gname, value in match.groupdict().items():
            original_name = group_name_map[gname]
            captured[original_name] = value.strip()

        # Step 4: Post-processing for known fields
        if "username" in captured:
            captured["username"] = captured["username"].lower().strip()

        if "creation_date" in captured:
            captured["creation_date"] = SnapchatAccountUtils.parse_creation_date(
                captured["creation_date"], index
            )
        else:
            captured["creation_date"] = datetime.utcnow().date()

        # Remove spaces from 2fa
        if "two_fa_secret" in captured:
            captured["two_fa_secret"] = re.sub(r"\s+", "", captured["two_fa_secret"])

        # Strip proxy
        if "proxy" in captured:
            captured["proxy"] = captured["proxy"].strip()

        # Optionally, generate a Snapchat link from username
        if "username" in captured and captured["username"]:
            captured["snapchat_link"] = (
                f"https://www.snapchat.com/add/{captured['username']}"
            )

        return captured

    @staticmethod
    def parse_account_line(line: str, index: int):
        """
        Parses a single line of input to extract username, password, creation date, and either a 2FA secret or proxy.

        :param line: The input line containing account details.
        :param index: The index of the line being processed (for error handling).
        :return: A dictionary with extracted account details.
        """
        fields = line.split()

        if len(fields) < 2:
            raise ValueError(f"Invalid format on line {index + 1}: {line}")

        # Extract username and password
        username = fields[0].strip().lower()
        password = fields[1].strip()

        # Check if there's a valid creation date
        potential_date = fields[2] if len(fields) > 2 else None
        if potential_date and (
                re.fullmatch(r"\d{4}", potential_date) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", potential_date)):
            creation_date = SnapchatAccountUtils.parse_creation_date(potential_date, index)
            remaining_fields = fields[3:]  # Remaining fields could be 2FA secret or proxy
        else:
            creation_date = datetime.utcnow().date()  # Default to today
            remaining_fields = fields[2:]  # Everything after password is 2FA or proxy

        # Determine if the remaining field is a 2FA secret or proxy
        extra_field = "".join(remaining_fields).replace(" ", "") if remaining_fields else None
        two_fa_secret = None
        proxy = None
        email = None
        email_password = None
        if extra_field:
            if re.fullmatch(r"[A-Za-z0-9]{32}", extra_field):
                two_fa_secret = extra_field  # It's a valid 2FA secret
            elif "@" in remaining_fields[0]:
                email = remaining_fields[0]
                email_password = remaining_fields[1]
            elif "." in extra_field:
                proxy = ":".join(remaining_fields)
            else:
                raise ValueError(
                    f"Invalid extra field on line {index + 1}: Must be a 32-character 2FA secret or a proxy (IP:PORT)"
                )

        # Construct Snapchat link
        snapchat_link = f"https://www.snapchat.com/add/{username}"

        return {
            "username": username,
            "password": password,
            "creation_date": creation_date,
            "two_fa_secret": two_fa_secret,
            "proxy": proxy,
            "snapchat_link": snapchat_link,
            "email": email,
            "email_password": email_password
        }

    @staticmethod
    def validate_patter(pattern: str, accepted_keys: list):
        """
        Parse the `pattern` to identify placeholders like {username}, {password}, etc.
        If any placeholder is not in `accepted_keys`, we raise an error.
        """
        # 1) Identify all placeholders in the pattern: e.g. {username}, {password}
        found_placeholders = re.findall(r"\{(.*?)\}", pattern)  # list of placeholders without braces

        # 2) Convert accepted_keys to a set for quick membership checks
        accepted_set = set(accepted_keys)

        # 3) Check each found placeholder
        for placeholder in found_placeholders:
            if placeholder not in accepted_set:
                # 4) Throw error if not in accepted list
                raise ValueError(
                    f"Invalid placeholder '{placeholder}'.\n"
                    f"Accepted placeholders are: {', '.join(sorted(accepted_set))}."
                )

        return True