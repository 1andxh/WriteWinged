import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

# using type check pattern
if TYPE_CHECKING:
    from src.auth.models import User
    from src.core.contributions import ContributionORM
    from src.core.proposals import ProposalORM
    from src.core.versions import VersionORM


class DocumentVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class DocumentState(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    ARCHIVED = "archived"


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    visibility: Mapped[DocumentVisibility] = mapped_column(
        SAEnum(DocumentVisibility, name="visibility_enum", native_enum=False),
        server_default=DocumentVisibility.PUBLIC.value,
        nullable=False,
    )
    state: Mapped[DocumentState] = mapped_column(
        SAEnum(DocumentState, name="document_state", native_enum=False),
        server_default=DocumentState.ACTIVE.value,
        nullable=False,
        index=True,
    )

    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey(
            "versions.id",
            use_alter=True,
            name="fk_published_version",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    draft_version_id: Mapped[uuid.UUID | None] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey(
            "versions.id", use_alter=True, name="fk_draft_version", ondelete="SET NULL"
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now(), onupdate=func.now()
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True
    )
    # relations
    versions: Mapped[list["VersionORM"]] = relationship(
        back_populates="document",
        foreign_keys="VersionORM.document_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    contributions: Mapped[list["ContributionORM"]] = relationship(
        back_populates="document",
        foreign_keys="ContributionORM.document_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    proposals: Mapped[list["ProposalORM"]] = relationship(
        back_populates="document",
        foreign_keys="ProposalORM.document_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    published_version: Mapped["VersionORM"] = relationship(
        foreign_keys=[published_version_id], post_update=True
    )
    draft_version: Mapped["VersionORM"] = relationship(
        foreign_keys=[draft_version_id], post_update=True
    )
    owner: Mapped["User"] = relationship(back_populates="documents")

    __table_args__ = (
        Index(
            "uq_documents_owner_title_active",
            "owner_id",
            func.lower(title),
            unique=True,
            postgresql_where=(deleted_at.is_(None)),
        ),
    )
