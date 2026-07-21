from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

from src.db.dependency import session
from src.mail.dependency import get_mail_service
from src.mail.service import MailService

from ..exceptions import InvalidCredentialsException, InvalidTokenException
from .models import User, UserSessionORM
from .schemas import TokenPayload
from .service import (
    AuthService,
    RefreshTokenService,
    SessionService,
    TokenService,
    UserService,
)
from .utils import decode_token

http_bearer = HTTPBearer()


async def get_user_service(session: session) -> UserService:
    return UserService(session)


user_service = Annotated[UserService, Depends(get_user_service)]


async def get_auth_service(session: session, user_service: user_service) -> AuthService:
    return AuthService(session, user_service)


auth_service = Annotated[AuthService, Depends(get_auth_service)]

mail_service = Annotated[MailService, Depends(get_mail_service)]


async def get_session_service(session: session) -> SessionService:
    return SessionService(session)


session_service = Annotated[SessionService, Depends(get_session_service)]


async def get_refresh_token_service(session: session) -> RefreshTokenService:
    return RefreshTokenService(session)


refresh_token_service = Annotated[
    RefreshTokenService, Depends(get_refresh_token_service)
]


async def get_token_service(
    session: session,
    session_service: session_service,
    refresh_token_service: refresh_token_service,
) -> TokenService:
    return TokenService(session, session_service, refresh_token_service)


token_service = Annotated[TokenService, Depends(get_token_service)]


async def get_current_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
) -> TokenPayload:
    payload = decode_token(credentials.credentials)
    if payload is None or payload.type != "access":
        raise InvalidTokenException()
    return payload


current_token_payload = Annotated[TokenPayload, Depends(get_current_token_payload)]


async def get_current_session(
    session_service: session_service, payload: current_token_payload
) -> UserSessionORM:
    user_session = await session_service.get_session_by_id(payload.sid)
    if user_session is None:
        raise InvalidTokenException()
    session_service.validate_session(user_session)
    return user_session


current_session = Annotated[UserSessionORM, Depends(get_current_session)]


async def get_current_user(
    user_service: user_service, user_session: current_session
) -> User:
    user = await user_service.get_user_by_id(user_session.user_id)
    if user is None:
        raise InvalidCredentialsException()
    return user
