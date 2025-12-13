from ..auth.models import User, UserRole
from sqlalchemy.ext.asyncio.session import AsyncSession
from pydantic import EmailStr

# from sqlmodel.ext.asyncio import
from sqlmodel import select, exists
from .schemas import UserCreateModel, GoogleUser, GoogleUserCreateModel
from .utils import hash_password


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def check_user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(self, dict: UserCreateModel, session: AsyncSession):
        user_data = dict.model_dump()
        new_user = User(**user_data)
        new_user.password_hash = hash_password(user_data["password"])
        new_user.role = UserRole.USER
        session.add(new_user)
        await session.commit()
        return new_user

    async def update_user(self, user: User, user_dict: dict, session: AsyncSession):
        for k, v in user_dict.items():
            setattr(user, k, v)

        await session.commit()
        return user


class GoogleUserService:
    async def create_user_from_google_info(
        self, google_user: GoogleUser, session: AsyncSession, is_verified: bool = False
    ) -> User:

        google_sub = google_user.sub
        email = google_user.email

        result = await session.execute(select(User).where(User.email == email))
        existing_user: User | None = result.scalar_one_or_none()

        if existing_user:
            existing_user.google_sub = google_sub
            await session.commit()
            await session.refresh(existing_user)
            return existing_user

        new_user_data = GoogleUserCreateModel(
            email=email,
            google_sub=google_user.sub,
            username=google_user.name,
            is_verified=is_verified,
        )
        data = new_user_data.model_dump()
        new_user = User(**data)
        new_user.role = UserRole.USER

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def get_user_by_google_sub(self, google_sub: str, session: AsyncSession):
        statement = select(User).where(User.google_sub == google_sub)
        result = await session.execute(statement)
        return result.one_or_none()
