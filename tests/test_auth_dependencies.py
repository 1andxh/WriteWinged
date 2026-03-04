import pytest

from src.auth.dependencies import get_current_user
from src.exceptions import InvalidCredentialsException


class DummyUserService:
    def __init__(self, user):
        self.user = user

    async def get_user_by_email(self, email, session):
        return self.user


@pytest.mark.asyncio
async def test_get_current_user_raises_when_user_missing(monkeypatch):
    monkeypatch.setattr(
        "src.auth.dependencies.user_service",
        DummyUserService(user=None),
    )

    with pytest.raises(InvalidCredentialsException):
        await get_current_user(
            token_data={"user": {"email": "missing@example.com"}},
            session=object(),
        )
