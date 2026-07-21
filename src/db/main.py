from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import config

async_engine = create_async_engine(
    url=config.DATABASE_URL,
    echo=config.SQL_ECHO,
    # NullPool: every checkout is a brand-new connection, none are reused
    # across requests. Ruled out an entire class of stale-connection bugs
    # while chasing the signup/login visibility issue.
    poolclass=NullPool,
    pool_pre_ping=True,
)

Session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


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
