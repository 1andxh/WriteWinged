from fastapi import Request, status, Depends
from annotated_doc import Doc
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from typing import Any, override, Annotated
from .utils import decode_token
from src.db.main import get_session
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from .service import UserService

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    def verify_token_data(self, token_data: dict[str, Any]):
        raise NotImplementedError("override this method in child class")

    async def __call__(self, request: Request) -> dict[str, Any] | None:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(
            request
        )

        if credentials is not None:
            token = credentials.credentials

        token_data = decode_token(token)

        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        self.verify_token_data(token_data)
        return token_data


class AccessTokenBearer(TokenBearer):
    @override
    def verify_token_data(self, token_data: dict[str, Any]):
        """checks tokent ytpe"""
        if token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provide an access token",
            )


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict[str, Any]):
        """checks tokent ytpe"""
        if not token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provide an refresh token",
            )


token_data = Annotated[dict[str, Any], Depends(AccessTokenBearer())]
session = Annotated[AsyncSession, Depends(get_session)]


async def get_currrent_user(token_data: token_data, session: session):
    user_email = token_data["user"]["email"]
    user = await user_service.get_user_by_email(user_email, session)
    return user
