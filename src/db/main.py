from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from typing import AsyncGenerator
from src.config import config
from sqlalchemy import text
import asyncio
import logging
import os
import time
from urllib.parse import urlparse

logger = logging.getLogger("writewinged.db")

async_engine = create_async_engine(
    url=config.DATABASE_URL,
    echo=config.SQL_ECHO,
    # connect_args={"statement_cache_size": 0},  # supabase to break prepared statements
)

Session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


def _database_target() -> tuple[str | None, int | None]:
    parsed = urlparse(config.DATABASE_URL)
    return parsed.hostname, parsed.port


def _is_production_like() -> bool:
    env_name = config.ENVIRONMENT.lower()
    return env_name in {"prod", "production"} or os.getenv("RENDER", "").lower() == "true"


async def init_db() -> None:
    """Ensure the database is reachable at startup with bounded retries."""
    host, port = _database_target()
    logger.info("database startup check target host=%s port=%s", host, port)

    if host in {"127.0.0.1", "localhost", "::1"} and _is_production_like():
        logger.warning(
            "DATABASE_URL points to localhost in a production-like environment."
        )

    max_wait = max(0, config.DB_STARTUP_MAX_WAIT_SECONDS)
    retry_interval = max(0.1, config.DB_STARTUP_RETRY_INTERVAL_SECONDS)
    start_time = time.monotonic()
    attempts = 0

    while True:
        attempts += 1
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            if attempts > 1:
                logger.info("database became reachable after %s attempts", attempts)
            return
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            remaining = max_wait - elapsed
            if remaining <= 0:
                logger.error(
                    (
                        "database startup check failed after %s attempts in %.2fs "
                        "(host=%s port=%s)"
                    ),
                    attempts,
                    elapsed,
                    host,
                    port,
                    exc_info=exc,
                )
                raise

            wait_for = min(retry_interval, remaining)
            logger.warning(
                (
                    "database not reachable yet (attempt=%s, elapsed=%.2fs/%.2fs, "
                    "retry_in=%.2fs): %s"
                ),
                attempts,
                elapsed,
                max_wait,
                wait_for,
                exc.__class__.__name__,
            )
            await asyncio.sleep(wait_for)


async def get_session() -> AsyncGenerator[AsyncSession, None]:

    async with Session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
