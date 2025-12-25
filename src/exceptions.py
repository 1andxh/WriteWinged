from fastapi import status
from starlette.status import HTTP_400_BAD_REQUEST


class WriteWingedExcpetion(Exception):
    """
    Base class for all Exceptions
    """

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthException(WriteWingedExcpetion):
    """Base class for all authentication/authorization Exceptions"""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(message, status_code)
