from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from .main import get_session

session = Annotated[AsyncSession, Depends(get_session)]
