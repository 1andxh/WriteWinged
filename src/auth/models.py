from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    func,
)
from datetime import datetime
import uuid
from enum import Enum
from ..db.base import Base
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.documents.models import DocumentORM


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    # redundant -- user with google_sub already shows auth provider


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="role_enum", native_enum=False),
        nullable=False,
    )

    # Always False for now: email verification was deferred post-MVP, so
    # nothing currently flips this to True. Don't gate access on it yet.
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        insert_default=func.now(),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=func.now(),
        nullable=False,
    )

    # relationship
    documents: Mapped[list["DocumentORM"]] = relationship(back_populates="owner")
    sessions: Mapped[list["UserSessionORM"]] = relationship(back_populates="user")


class UserSessionORM(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    refresh_tokens: Mapped[list["RefreshTokenORM"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="chk_user_session_expiry"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="chk_user_session_revocation",
        ),
    )


class RefreshTokenORM(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped["UserSessionORM"] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="chk_refresh_token_expiry"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="chk_refresh_token_revocation",
        ),
    )
