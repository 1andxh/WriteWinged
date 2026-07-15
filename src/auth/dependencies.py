from fastapi import Request, Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from typing import Any, Annotated
from .utils import decode_token
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .service import UserService
from ..exceptions import (
    InvalidTokenException,
    InvalidCredentialsException,
)

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict[str, Any] | None:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(
            request
        )

        if credentials is None:
            raise InvalidTokenException()

        token = credentials.credentials

        token_data = decode_token(token)

        if token_data is None:
            raise InvalidTokenException()
        return token_data


token_data = Annotated[dict[str, Any], Depends(TokenBearer())]
session = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(token_data: token_data, session: session):
    user_email = token_data["user"]["email"]
    user = await user_service.get_user_by_email(user_email, session)
    if user is None:
        raise InvalidCredentialsException()
    return user
