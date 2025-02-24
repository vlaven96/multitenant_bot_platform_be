from typing import Optional


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    """
    Converts a string to a boolean if possible.
    Accepted values:
    - True: "true", "1", "yes" (case-insensitive)
    - False: "false", "0", "no" (case-insensitive)
    - None: if the input is None
    """
    if value is None:
        return None
    value = value.strip().lower()  # Normalize the input
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")