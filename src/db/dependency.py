from typing import Annotated
from .main import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

session = Annotated[AsyncSession, Depends(get_session)]
