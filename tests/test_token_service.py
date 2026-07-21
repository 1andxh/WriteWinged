import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.auth.models import RefreshTokenORM, UserSessionORM
from src.auth.service import TokenService
from src.auth.utils import decode_token
from src.exceptions import InvalidTokenException, RevokedTokenException


class SimpleUser:
    def __init__(self, user_id: uuid.UUID) -> None:
        self.id = user_id


class FakeSessionService:
    def __init__(self):
        self.sessions_by_id: dict[uuid.UUID, UserSessionORM] = {}
        self.revoked: list[uuid.UUID] = []

    async def create_session(self, user_id, user_agent=None, ip_address=None):
        user_session = UserSessionORM(
            id=uuid.uuid4(),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.sessions_by_id[user_session.id] = user_session
        return user_session

    async def get_session_by_id(self, session_id):
        return self.sessions_by_id.get(session_id)

    async def revoke_session(self, session_id):
        self.revoked.append(session_id)
        user_session = self.sessions_by_id.get(session_id)
        if user_session is not None:
            user_session.revoked_at = datetime.now(timezone.utc)

    def validate_session(self, user_session):
        if user_session.revoked_at is not None:
            raise RevokedTokenException()
        if user_session.expires_at <= datetime.now(timezone.utc):
            raise InvalidTokenException()


class FakeRefreshTokenService:
    def __init__(self):
        self.tokens_by_raw: dict[str, RefreshTokenORM] = {}
        self.rotated: list[RefreshTokenORM] = []
        self.revoked_families: list[uuid.UUID] = []

    def seed(self, raw_token: str, token: RefreshTokenORM) -> None:
        self.tokens_by_raw[raw_token] = token

    async def issue(self, session_id, family_id=None):
        raw = f"refresh-{uuid.uuid4()}"
        self.tokens_by_raw[raw] = RefreshTokenORM(
            id=uuid.uuid4(),
            session_id=session_id,
            family_id=family_id or uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        return raw

    async def get_by_raw_token(self, raw_token):
        return self.tokens_by_raw.get(raw_token)

    async def rotate(self, token):
        self.rotated.append(token)
        token.revoked_at = datetime.now(timezone.utc)
        return await self.issue(token.session_id, family_id=token.family_id)

    async def revoke_family(self, family_id):
        self.revoked_families.append(family_id)

    async def revoke(self, raw_token):
        token = self.tokens_by_raw.get(raw_token)
        if token is not None:
            token.revoked_at = datetime.now(timezone.utc)
        return token


class FakeSession:
    async def commit(self):
        return None


def make_service():
    session_service = FakeSessionService()
    refresh_token_service = FakeRefreshTokenService()
    token_service = TokenService(
        session=FakeSession(),
        session_service=session_service,
        refresh_token_service=refresh_token_service,
    )
    return token_service, session_service, refresh_token_service


@pytest.mark.asyncio
async def test_issue_token_pair_creates_session_and_matching_access_token():
    token_service, session_service, refresh_token_service = make_service()
    user_id = uuid.uuid4()

    tokens = await token_service.issue_token_pair(
        SimpleUser(user_id), user_agent="pytest", ip_address="127.0.0.1"
    )

    assert len(session_service.sessions_by_id) == 1
    user_session = next(iter(session_service.sessions_by_id.values()))
    assert tokens.refresh_token in refresh_token_service.tokens_by_raw

    payload = decode_token(tokens.access_token)
    assert payload.sub == user_id
    assert payload.sid == user_session.id


@pytest.mark.asyncio
async def test_refresh_tokens_rotates_and_mints_access_token_for_same_session():
    token_service, session_service, refresh_token_service = make_service()
    user_session = await session_service.create_session(uuid.uuid4())
    existing = RefreshTokenORM(
        id=uuid.uuid4(),
        session_id=user_session.id,
        family_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    refresh_token_service.seed("old-token", existing)

    tokens = await token_service.refresh_tokens("old-token")

    assert refresh_token_service.rotated == [existing]
    payload = decode_token(tokens.access_token)
    assert payload.sid == user_session.id
    assert payload.sub == user_session.user_id


@pytest.mark.asyncio
async def test_refresh_tokens_raises_for_unknown_token():
    token_service, _, _ = make_service()

    with pytest.raises(InvalidTokenException):
        await token_service.refresh_tokens("unknown-token")


@pytest.mark.asyncio
async def test_refresh_tokens_raises_for_expired_token():
    token_service, session_service, refresh_token_service = make_service()
    user_session = await session_service.create_session(uuid.uuid4())
    expired = RefreshTokenORM(
        id=uuid.uuid4(),
        session_id=user_session.id,
        family_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    refresh_token_service.seed("expired-token", expired)

    with pytest.raises(InvalidTokenException):
        await token_service.refresh_tokens("expired-token")


@pytest.mark.asyncio
async def test_refresh_tokens_on_reuse_revokes_family_and_session():
    token_service, session_service, refresh_token_service = make_service()
    user_session = await session_service.create_session(uuid.uuid4())
    family_id = uuid.uuid4()
    reused = RefreshTokenORM(
        id=uuid.uuid4(),
        session_id=user_session.id,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    refresh_token_service.seed("stolen-token", reused)

    with pytest.raises(RevokedTokenException):
        await token_service.refresh_tokens("stolen-token")

    assert refresh_token_service.revoked_families == [family_id]
    assert session_service.revoked == [user_session.id]


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token_and_its_session():
    token_service, session_service, refresh_token_service = make_service()
    user_session = await session_service.create_session(uuid.uuid4())
    token = RefreshTokenORM(
        id=uuid.uuid4(),
        session_id=user_session.id,
        family_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    refresh_token_service.seed("logout-token", token)

    await token_service.logout("logout-token")

    assert token.revoked_at is not None
    assert session_service.revoked == [user_session.id]


@pytest.mark.asyncio
async def test_logout_is_a_noop_for_unknown_token():
    token_service, session_service, _ = make_service()

    await token_service.logout("unknown-token")

    assert session_service.revoked == []
