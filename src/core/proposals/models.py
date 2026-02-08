import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from typing import Optional
from enum import Enum
from datetime import datetime, timezone
from src.db.base import Base
from src.core.documents import DocumentORM


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

    # relationship
    document: Mapped["DocumentORM"] = relationship(
        back_populates="proposals", foreign_keys=[document_id]
    )
