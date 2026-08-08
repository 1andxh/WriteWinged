import uuid
from datetime import datetime
from enum import Enum

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth import User
from src.core.documents import DocumentORM
from src.db.base import Base


class ContributionORM(Base):
    __tablename__ = "contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    document: Mapped["DocumentORM"] = relationship(back_populates="contributions")
    user: Mapped["User"] = relationship(lazy="joined")

    @property
    def contributor_id(self) -> uuid.UUID:

        return self.user_id

    __table_args__ = (
        UniqueConstraint(
            "document_id", "user_id", name="uq_contribution_document_user"
        ),
    )


class ContributionRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class ContributionRequestORM(Base):
    __tablename__ = "contribution_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[ContributionRequestStatus] = mapped_column(
        SAEnum(
            ContributionRequestStatus,
            name="contribution_request_status",
            native_enum=False,
        ),
        default=ContributionRequestStatus.PENDING,
        server_default=ContributionRequestStatus.PENDING.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    document: Mapped["DocumentORM"] = relationship()
    user: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (
        # A user may have at most one *pending* request per document, but can
        # re-request after a previous one was declined.
        Index(
            "uq_contribution_request_pending_document_user",
            "document_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )
