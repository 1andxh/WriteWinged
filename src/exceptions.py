from fastapi import status
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED


class WriteWingedException(Exception):
    """
    Base class for all Exceptions
    """

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthException(WriteWingedException):
    """Base class for all authentication/authorization Exceptions"""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(message, status_code)


class InvalidTokenException(AuthException):
    """Raised when a token is invalid or has expired"""

    def __init__(
        self,
        message: str = "Invalid or expired token",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ):
        super().__init__(message, status_code)


class RevokedTokenException(AuthException):
    """Raised when a revoked token is provided"""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__("Token has been revoked", status_code)


class AccessTokenRequiredException(AuthException):
    """Raised when an access token is required but not provied"""

    def __init__(self):
        super().__init__(
            "Acess token required", status_code=status.HTTP_401_UNAUTHORIZED
        )


class RefreshTokenRequiredException(AuthException):
    """Raised when an refresh token is required but not provied"""

    def __init__(self):
        super().__init__(
            "Provide refresh token", status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidCredentialsException(AuthException):
    """Raised when invalid credential is provided login"""

    def __init__(self):
        super().__init__(
            "Invalid email or password", status_code=status.HTTP_401_UNAUTHORIZED
        )


class UserAlreadyExistsException(AuthException):
    """Raised when an attempt to sign up with an email that already exists is made"""

    def __init__(self, email: str):
        self.email = email
        super().__init__(
            f"User with email '{email}' already exists",
            status_code=status.HTTP_409_CONFLICT,
        )


class UserNotFoundException(AuthException):
    """Raised when user not found"""

    def __init__(self):
        super().__init__("User not found", status_code=status.HTTP_404_NOT_FOUND)


class UserNotVerifiedException(AuthException):
    """Raise when user isn't verified"""

    def __init__(self):
        super().__init__(
            "User account not verified. Check email to complete verification",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# # SUGGESTION EXCEPTIONS
# class SuggestionServiceException(WriteWingedException):
#     """Exceptions for service layer logic """

#     def __init__(self, message: str):
#         self.message = message
#         Exception.__init__(self, self.message)


# class ResourceNotFoundError(SuggestionServiceException):
#     """Raised when target resourse is not found"""

#     def __init__(self, message: str):
#         super().__init__(message)


# class DocumentNotAcceptingSuggestionsError(SuggestionServiceException):
#     """Document is archived/locked, can't accept suggestions"""

#     def __init__(self, message: str = "Document not accepting suggestions"):
#         super().__init__(message)


# DOCUMENT EXCEPTIONS
class DocumentError(WriteWingedException):
    """Base exception for document domain errors."""


class DocumentNotFound(DocumentError):
    """Raised when document is not found"""

    def __init__(self, message: str = "Document not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class DocumentPermissionDenied(DocumentError):
    """Raised when actor lacks permission"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class InvalidDocumentState(DocumentError):
    """Raised when state transition contradicts allowed transistions"""

    def __init__(self, message: str = "Invalid document state"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class DocumentNotMutable(DocumentError):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class DocumentTitleConflict(DocumentError):
    def __init__(self, message: str = "A document with this title already exists"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


# VERSION EXCEPTIONS
class VersionDoesNotExist(DocumentError):
    """Raised when version does not exists or is not found"""

    def __init__(self, message: str = "Version does not exist"):
        self.message = message
        Exception.__init__(self, self.message)


class VersionMismatch(DocumentError):
    def __init__(self, message: str = "Version does not belong to document"):
        self.message = message
        Exception.__init__(self, self.message)
