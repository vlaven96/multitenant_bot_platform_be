class SnapkatApiError(Exception):
    def __init__(self, error_code: int, message: str):
        super().__init__(f"SnapkatApiError {error_code}: {message}")
        self.error_code = error_code
        self.message = message

class SnapkatHttpError(Exception):
    """Exception for HTTP-related failures"""
    def __init__(self, status_code, response_text):
        super().__init__(f"HTTP {status_code}: {response_text}")
        self.status_code = status_code
        self.response_text = response_text