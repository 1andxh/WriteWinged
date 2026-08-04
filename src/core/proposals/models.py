import uuid
from datetime import datetime
from enum import Enum

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth.models import User
from src.core.documents import DocumentORM
from src.core.versions import VersionORM
from src.db.base import Base


class ProposalState(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ProposalORM(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("versions.id", ondelete="SET NULL")
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[ProposalState] = mapped_column(
        SAEnum(ProposalState, name="proposal_state", native_enum=False),
        nullable=False,
        default=ProposalState.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationship
    document: Mapped["DocumentORM"] = relationship(
        back_populates="proposals", foreign_keys=[document_id]
    )
    author: Mapped["User"] = relationship(lazy="joined", foreign_keys=[author_id])
    base_version: Mapped["VersionORM | None"] = relationship(
        foreign_keys=[base_version_id]
    )
