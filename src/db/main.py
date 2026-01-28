from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from typing import AsyncGenerator, Annotated
from src.db.base import Base
from src.config import config
from src.auth.models import User
from ..core.documents.models import DocumentORM
from src.core.versions.models import VersionORM
from src.core.contributions.models import ContributionORM

# note: import models before metadata.create_all()

async_engine = create_async_engine(
    url=config.DATABASE_URL,
    echo=True,
)

Session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """create db connection"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# todo: get_session
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
