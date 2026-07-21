import uuid

import pytest

from src.auth.models import User, UserRole
from src.auth.schemas import GoogleUser
from src.auth.service import AuthService, UserService


class DummyResult:
    def __init__(self, one=None):
        self._one = one

    def scalar_one_or_none(self):
        return self._one


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


def make_user(**overrides) -> User:
    fields = dict(
        id=uuid.uuid4(),
        email="writer@example.com",
        username="writer",
        role=UserRole.USER,
        google_sub=None,
        is_verified=False,
    )
    fields.update(overrides)
    return User(**fields)


def make_google_user(**overrides) -> GoogleUser:
    fields = dict(sub="google-sub-123", email="writer@example.com", name="Writer Name")
    fields.update(overrides)
    return GoogleUser(**fields)


@pytest.mark.asyncio
async def test_authenticate_via_google_returns_existing_user_by_sub():
    existing = make_user(google_sub="google-sub-123")
    session = QueueSession(results=[DummyResult(one=existing)])
    service = AuthService(session, UserService(session))

    user = await service.authenticate_via_google(make_google_user())

    assert user is existing
    assert session.added == []


@pytest.mark.asyncio
async def test_authenticate_via_google_links_existing_user_found_by_email():
    existing = make_user(google_sub=None, is_verified=False)
    session = QueueSession(
        results=[DummyResult(one=None), DummyResult(one=existing)]
    )
    service = AuthService(session, UserService(session))

    user = await service.authenticate_via_google(make_google_user())

    assert user is existing
    assert user.google_sub == "google-sub-123"
    assert user.is_verified is True


@pytest.mark.asyncio
async def test_authenticate_via_google_creates_new_user_when_none_found():
    session = QueueSession(
        results=[DummyResult(one=None), DummyResult(one=None), DummyResult(one=None)]
    )
    service = AuthService(session, UserService(session))

    user = await service.authenticate_via_google(make_google_user())

    assert len(session.added) == 1
    assert user is session.added[0]
    assert user.email == "writer@example.com"
    assert user.username == "Writer Name"
    assert user.google_sub == "google-sub-123"
    assert user.is_verified is True
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_create_google_user_disambiguates_colliding_username():
    taken_by = make_user(username="Writer Name")
    session = QueueSession(results=[DummyResult(one=taken_by)])
    service = UserService(session)

    user = await service.create_google_user(
        make_google_user(sub="abcdef123456", name="Writer Name")
    )

    assert user.username != "Writer Name"
    assert user.username.endswith("123456")
