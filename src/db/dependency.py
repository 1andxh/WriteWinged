from typing import Annotated
from .main import get_session
from sqlalchemy.ext.asyncio.session import AsyncSession
from fastapi import Depends

# inject in route handler
session = Annotated[AsyncSession, Depends(get_session)]
