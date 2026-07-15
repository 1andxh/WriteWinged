import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.auth.models import RefreshTokenORM
from src.auth.service import RefreshTokenService
from src.auth.utils import hash_refresh_token


class DummyResult:
    def __init__(self, one=None, scalars_list=None):
        self._one = one
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list


class QueueSession:
    """Fake AsyncSession that returns queued results in call order."""

    def __init__(self, results):
        self._results = list(results)
        self.added = []

    async def execute(self, statement):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None


def make_token(
    raw_token: str, session_id: uuid.UUID, *, revoked: bool = False
) -> RefreshTokenORM:
    return RefreshTokenORM(
        id=uuid.uuid4(),
        session_id=session_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=(
            datetime.now(timezone.utc) - timedelta(minutes=5) if revoked else None
        ),
    )


@pytest.mark.asyncio
async def test_issue_stores_hashed_token_and_returns_raw_value():
    session = QueueSession(results=[])
    service = RefreshTokenService(session)
    session_id = uuid.uuid4()

    raw_token = await service.issue(session_id)

    assert len(session.added) == 1
    stored = session.added[0]
    assert stored.session_id == session_id
    assert stored.token_hash == hash_refresh_token(raw_token)
    assert stored.token_hash != raw_token


@pytest.mark.asyncio
async def test_issue_reuses_family_id_when_given():
    session = QueueSession(results=[])
    service = RefreshTokenService(session)
    family_id = uuid.uuid4()

    await service.issue(uuid.uuid4(), family_id=family_id)

    assert session.added[0].family_id == family_id


@pytest.mark.asyncio
async def test_get_by_raw_token_returns_none_when_missing():
    session = QueueSession(results=[DummyResult(one=None)])
    service = RefreshTokenService(session)

    result = await service.get_by_raw_token("unknown-token")

    assert result is None


@pytest.mark.asyncio
async def test_rotate_revokes_token_and_issues_replacement_in_same_family():
    session_id = uuid.uuid4()
    token = make_token("existing-token", session_id)

    session = QueueSession(results=[])
    service = RefreshTokenService(session)

    new_raw_token = await service.rotate(token)

    assert token.revoked_at is not None
    assert new_raw_token != "existing-token"
    assert len(session.added) == 1
    assert session.added[0].family_id == token.family_id
    assert session.added[0].session_id == session_id


@pytest.mark.asyncio
async def test_revoke_marks_token_revoked():
    token = make_token("logout-token", uuid.uuid4())
    session = QueueSession(results=[DummyResult(one=token)])
    service = RefreshTokenService(session)

    result = await service.revoke("logout-token")

    assert result is token
    assert token.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_is_a_noop_for_unknown_token():
    session = QueueSession(results=[DummyResult(one=None)])
    service = RefreshTokenService(session)

    result = await service.revoke("unknown-token")

    assert result is None


@pytest.mark.asyncio
async def test_revoke_family_revokes_all_active_tokens_in_family():
    family_id = uuid.uuid4()
    active_one = make_token("a", uuid.uuid4())
    active_two = make_token("b", uuid.uuid4())

    session = QueueSession(
        results=[DummyResult(scalars_list=[active_one, active_two])]
    )
    service = RefreshTokenService(session)

    await service.revoke_family(family_id)

    assert active_one.revoked_at is not None
    assert active_two.revoked_at is not None
