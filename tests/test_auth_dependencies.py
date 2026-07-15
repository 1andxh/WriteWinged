import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.security.http import HTTPAuthorizationCredentials

from src.auth.dependencies import (
    get_current_session,
    get_current_token_payload,
    get_current_user,
)
from src.auth.models import UserSessionORM
from src.auth.schemas import TokenPayload
from src.auth.service import SessionService
from src.auth.utils import create_access_token, jwt_algorithm, jwt_secret_key
from src.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    RevokedTokenException,
)


class DummyUserService:
    def __init__(self, user):
        self.user = user

    async def get_user_by_id(self, user_id):
        return self.user


class DummySessionService(SessionService):
    """Reuses SessionService.validate_session (pure, no DB) with a canned lookup."""

    def __init__(self, user_session):
        self.user_session = user_session

    async def get_session_by_id(self, session_id):
        return self.user_session


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def make_session(*, revoked: bool = False, expired: bool = False) -> UserSessionORM:
    return UserSessionORM(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc)
        + (timedelta(days=-1) if expired else timedelta(days=1)),
        revoked_at=(
            datetime.now(timezone.utc) - timedelta(minutes=5) if revoked else None
        ),
    )


def make_payload(session_id: uuid.UUID) -> TokenPayload:
    now = int(datetime.now(timezone.utc).timestamp())
    return TokenPayload(
        sub=uuid.uuid4(), sid=session_id, type="access", iat=now, exp=now + 60,
        jti=str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_get_current_token_payload_accepts_valid_access_token():
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, session_id=session_id)

    payload = await get_current_token_payload(bearer(token))

    assert payload.sub == user_id
    assert payload.sid == session_id
    assert payload.type == "access"


@pytest.mark.asyncio
async def test_get_current_token_payload_rejects_garbage_token():
    with pytest.raises(InvalidTokenException):
        await get_current_token_payload(bearer("not-a-jwt"))


@pytest.mark.asyncio
async def test_get_current_token_payload_rejects_non_access_token_type():
    now = int(datetime.now(timezone.utc).timestamp())
    raw_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "type": "refresh",
            "iat": now,
            "exp": now + 60,
            "jti": str(uuid.uuid4()),
        },
        key=jwt_secret_key,
        algorithm=jwt_algorithm,
    )

    with pytest.raises(InvalidTokenException):
        await get_current_token_payload(bearer(raw_token))


@pytest.mark.asyncio
async def test_get_current_session_returns_active_session():
    user_session = make_session()
    payload = make_payload(session_id=user_session.id)

    result = await get_current_session(DummySessionService(user_session), payload)

    assert result is user_session


@pytest.mark.asyncio
async def test_get_current_session_raises_when_session_missing():
    payload = make_payload(session_id=uuid.uuid4())

    with pytest.raises(InvalidTokenException):
        await get_current_session(DummySessionService(None), payload)


@pytest.mark.asyncio
async def test_get_current_session_raises_when_session_revoked():
    user_session = make_session(revoked=True)
    payload = make_payload(session_id=user_session.id)

    with pytest.raises(RevokedTokenException):
        await get_current_session(DummySessionService(user_session), payload)


@pytest.mark.asyncio
async def test_get_current_session_raises_when_session_expired():
    user_session = make_session(expired=True)
    payload = make_payload(session_id=user_session.id)

    with pytest.raises(InvalidTokenException):
        await get_current_session(DummySessionService(user_session), payload)


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_session():
    user_session = make_session()

    user = await get_current_user(
        user_service=DummyUserService(user="the-user"), user_session=user_session
    )

    assert user == "the-user"


@pytest.mark.asyncio
async def test_get_current_user_raises_when_user_missing():
    user_session = make_session()

    with pytest.raises(InvalidCredentialsException):
        await get_current_user(
            user_service=DummyUserService(user=None), user_session=user_session
        )
