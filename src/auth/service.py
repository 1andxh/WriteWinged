from ..auth.models import User, UserRole
from sqlalchemy.ext.asyncio.session import AsyncSession

from sqlmodel import select
from .schemas import UserCreateModel
from .utils import hash_password


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession) -> User | None:
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def check_user_exists(self, email: str, session: AsyncSession) -> bool:
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(self, payload: UserCreateModel, session: AsyncSession):
        user_data = payload.model_dump()
        password = user_data.pop("password")
        new_user = User(**user_data)
        new_user.password_hash = hash_password(password)
        new_user.role = UserRole.USER
        session.add(new_user)
        await session.flush()
        return new_user

    async def update_user(self, user: User, user_dict: dict, session: AsyncSession):
        for k, v in user_dict.items():
            setattr(user, k, v)

        await session.flush()
        return user
