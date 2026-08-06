import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..auth.models import RefreshTokenORM, User, UserRole, UserSessionORM
from ..exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    RevokedTokenException,
    UserAlreadyExistsException,
)
from .schemas import GoogleUser, UserCreateModel
from .utils import (
    REFRESH_TOKEN_EXPIRY,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_user_by_google_sub(self, google_sub: str) -> User | None:
        statement = select(User).where(User.google_sub == google_sub)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def check_user_exists(self, email: str) -> bool:
        return await self.get_user_by_email(email) is not None

    async def check_username_exists(self, username: str) -> bool:
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def create_user(self, payload: UserCreateModel) -> User:
        user_data = payload.model_dump()
        password = user_data.pop("password")
        new_user = User(**user_data)
        new_user.password_hash = hash_password(password)
        new_user.role = UserRole.USER
        self.session.add(new_user)
        await self.session.flush()
        return new_user

    async def update_user(self, user: User, user_dict: dict) -> User:
        for k, v in user_dict.items():
            setattr(user, k, v)

        await self.session.flush()
        return user

    async def set_password(self, user: User, new_password: str) -> User:
        user.password_hash = hash_password(new_password)
        await self.session.flush()
        return user

    async def create_google_user(self, google_user: GoogleUser) -> User:
        username = google_user.name
        if await self.check_username_exists(username):
            username = f"{google_user.name} {google_user.sub[-6:]}"

        new_user = User(
            email=google_user.email,
            username=username,
            google_sub=google_user.sub,
            role=UserRole.USER,
            is_verified=True,
        )
        self.session.add(new_user)
        await self.session.flush()
        return new_user


class AuthService:
    def __init__(self, session: AsyncSession, user_service: UserService) -> None:
        self.session = session
        self.user_service = user_service

    async def register(self, payload: UserCreateModel) -> User:
        if await self.user_service.check_user_exists(payload.email):
            raise UserAlreadyExistsException(payload.email)
        return await self.user_service.create_user(payload)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_service.get_user_by_email(email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsException()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsException()
        return user

    async def authenticate_via_google(self, google_user: GoogleUser) -> User:
        user = await self.user_service.get_user_by_google_sub(google_user.sub)
        if user is not None:
            return user

        user = await self.user_service.get_user_by_email(google_user.email)
        if user is not None:
            user.google_sub = google_user.sub
            user.is_verified = True
            await self.session.flush()
            return user

        return await self.user_service.create_google_user(google_user)


class SessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        user_id: uuid.UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> UserSessionORM:
        user_session = UserSessionORM(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRY,
        )
        self.session.add(user_session)
        await self.session.flush()
        return user_session

    async def get_session_by_id(self, session_id: uuid.UUID) -> UserSessionORM | None:
        return await self.session.get(UserSessionORM, session_id)

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        user_session = await self.get_session_by_id(session_id)
        if user_session is not None and user_session.revoked_at is None:
            user_session.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()

    def validate_session(self, user_session: UserSessionORM) -> None:
        if user_session.revoked_at is not None:
            raise RevokedTokenException()
        if user_session.expires_at <= datetime.now(timezone.utc):
            raise InvalidTokenException()


class RefreshTokenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def issue(
        self, session_id: uuid.UUID, family_id: uuid.UUID | None = None
    ) -> str:
        raw_token = generate_refresh_token()
        token = RefreshTokenORM(
            session_id=session_id,
            token_hash=hash_refresh_token(raw_token),
            family_id=family_id or uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRY,
        )
        self.session.add(token)
        await self.session.flush()
        return raw_token

    async def get_by_raw_token(self, raw_token: str) -> RefreshTokenORM | None:
        statement = select(RefreshTokenORM).where(
            RefreshTokenORM.token_hash == hash_refresh_token(raw_token)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def rotate(self, token: RefreshTokenORM) -> str:
        """Revoke `token` and issue its replacement in the same rotation family."""
        token.revoked_at = datetime.now(timezone.utc)
        new_raw_token = await self.issue(token.session_id, family_id=token.family_id)
        return new_raw_token

    async def revoke(self, raw_token: str) -> RefreshTokenORM | None:
        token = await self.get_by_raw_token(raw_token)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()
        return token

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        statement = select(RefreshTokenORM).where(
            RefreshTokenORM.family_id == family_id,
            RefreshTokenORM.revoked_at.is_(None),
        )
        result = await self.session.execute(statement)
        now = datetime.now(timezone.utc)
        for active_token in result.scalars().all():
            active_token.revoked_at = now
        await self.session.flush()


@dataclass(slots=True, frozen=True)
class AccessTokens:
    access_token: str
    refresh_token: str


class TokenService:
    def __init__(
        self,
        session: AsyncSession,
        session_service: SessionService,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self.session = session
        self.session_service = session_service
        self.refresh_token_service = refresh_token_service

    async def issue_token_pair(
        self,
        user: User,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AccessTokens:
        user_session = await self.session_service.create_session(
            user.id, user_agent=user_agent, ip_address=ip_address
        )
        refresh_token = await self.refresh_token_service.issue(user_session.id)
        access_token = create_access_token(user_id=user.id, session_id=user_session.id)
        return AccessTokens(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, raw_refresh_token: str) -> AccessTokens:
        token = await self.refresh_token_service.get_by_raw_token(raw_refresh_token)
        if token is None:
            raise InvalidTokenException()

        if token.revoked_at is not None:
            await self.refresh_token_service.revoke_family(token.family_id)
            await self.session_service.revoke_session(token.session_id)
            raise RevokedTokenException()

        if token.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenException()

        user_session = await self.session_service.get_session_by_id(token.session_id)
        if user_session is None:
            raise InvalidTokenException()
        self.session_service.validate_session(user_session)

        new_raw_token = await self.refresh_token_service.rotate(token)
        access_token = create_access_token(
            user_id=user_session.user_id, session_id=user_session.id
        )
        return AccessTokens(access_token=access_token, refresh_token=new_raw_token)

    async def logout(self, raw_refresh_token: str) -> None:
        token = await self.refresh_token_service.revoke(raw_refresh_token)
        if token is not None:
            await self.session_service.revoke_session(token.session_id)
