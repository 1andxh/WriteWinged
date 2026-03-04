import pytest

from src.config import Config
from src.db import main as db_main


class FlakyEngine:
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    def connect(self):
        engine = self

        class ConnCtx:
            async def __aenter__(self):
                engine.calls += 1
                if engine.calls <= engine.fail_times:
                    raise ConnectionRefusedError("db unavailable")
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def execute(self, _statement):
                return 1

        return ConnCtx()


@pytest.mark.asyncio
async def test_init_db_succeeds_without_retry(monkeypatch):
    engine = FlakyEngine(fail_times=0)
    monkeypatch.setattr(db_main, "async_engine", engine)
    monkeypatch.setattr(db_main.config, "DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/app")
    monkeypatch.setattr(db_main.config, "DB_STARTUP_MAX_WAIT_SECONDS", 1)
    monkeypatch.setattr(db_main.config, "DB_STARTUP_RETRY_INTERVAL_SECONDS", 0.1)

    await db_main.init_db()

    assert engine.calls == 1


@pytest.mark.asyncio
async def test_init_db_retries_then_succeeds(monkeypatch):
    engine = FlakyEngine(fail_times=2)
    monkeypatch.setattr(db_main, "async_engine", engine)
    monkeypatch.setattr(db_main.config, "DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/app")
    monkeypatch.setattr(db_main.config, "DB_STARTUP_MAX_WAIT_SECONDS", 5)
    monkeypatch.setattr(db_main.config, "DB_STARTUP_RETRY_INTERVAL_SECONDS", 1)

    slept = []
    clock = {"now": 0.0}

    async def fake_sleep(seconds):
        slept.append(seconds)
        clock["now"] += seconds

    def fake_monotonic():
        return clock["now"]

    monkeypatch.setattr(db_main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(db_main.time, "monotonic", fake_monotonic)

    await db_main.init_db()

    assert engine.calls == 3
    assert slept == [1, 1]


@pytest.mark.asyncio
async def test_init_db_fails_after_timeout(monkeypatch):
    engine = FlakyEngine(fail_times=99)
    monkeypatch.setattr(db_main, "async_engine", engine)
    monkeypatch.setattr(db_main.config, "DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/app")
    monkeypatch.setattr(db_main.config, "DB_STARTUP_MAX_WAIT_SECONDS", 2)
    monkeypatch.setattr(db_main.config, "DB_STARTUP_RETRY_INTERVAL_SECONDS", 1)

    clock = {"now": 0.0}

    async def fake_sleep(seconds):
        clock["now"] += seconds

    def fake_monotonic():
        return clock["now"]

    monkeypatch.setattr(db_main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(db_main.time, "monotonic", fake_monotonic)

    with pytest.raises(ConnectionRefusedError):
        await db_main.init_db()

    assert engine.calls == 3


def test_config_startup_retry_defaults():
    cfg = Config(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://u:p@db:5432/app",
        JWT_SECRET="secret",
        JWT_ALGORITHM="HS256",
        API_VERSION="v1",
        GOOGLE_CLIENT_ID="client",
        GOOGLE_CLIENT_SECRET="secret",
        GOOGLE_REDIRECT_URI="https://example.com/auth/google",
        MIDDLEWARE_SECRET="middleware",
        REDIS_URL="redis://redis:6379/0",
        MAIL_USERNAME="mail-user",
        MAIL_PASSWORD="mail-pass",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.example.com",
        MAIL_FROM="noreply@example.com",
        MAIL_FROM_NAME="WriteWinged",
        DOMAIN="example.com",
        EMAIL_SECRET="email-secret",
        PASSWORD_RESET_SECRET="reset-secret",
    )

    assert cfg.DB_STARTUP_MAX_WAIT_SECONDS == 30
    assert cfg.DB_STARTUP_RETRY_INTERVAL_SECONDS == 2


def test_config_startup_retry_overrides():
    cfg = Config(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://u:p@db:5432/app",
        DB_STARTUP_MAX_WAIT_SECONDS=45,
        DB_STARTUP_RETRY_INTERVAL_SECONDS=5,
        JWT_SECRET="secret",
        JWT_ALGORITHM="HS256",
        API_VERSION="v1",
        GOOGLE_CLIENT_ID="client",
        GOOGLE_CLIENT_SECRET="secret",
        GOOGLE_REDIRECT_URI="https://example.com/auth/google",
        MIDDLEWARE_SECRET="middleware",
        REDIS_URL="redis://redis:6379/0",
        MAIL_USERNAME="mail-user",
        MAIL_PASSWORD="mail-pass",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.example.com",
        MAIL_FROM="noreply@example.com",
        MAIL_FROM_NAME="WriteWinged",
        DOMAIN="example.com",
        EMAIL_SECRET="email-secret",
        PASSWORD_RESET_SECRET="reset-secret",
    )

    assert cfg.DB_STARTUP_MAX_WAIT_SECONDS == 45
    assert cfg.DB_STARTUP_RETRY_INTERVAL_SECONDS == 5
