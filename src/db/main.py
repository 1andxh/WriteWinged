from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from typing import AsyncGenerator
from src.config import config
from sqlalchemy import text

async_engine = create_async_engine(
    url=config.DATABASE_URL,
    echo=config.SQL_ECHO,
    # connect_args={"statement_cache_size": 0},  # supabase to break prepared statements
)

Session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Ensure the database is reachable at startup."""
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


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
