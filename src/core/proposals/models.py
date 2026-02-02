import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from typing import Optional
from enum import Enum
from datetime import datetime, timezone
from src.db.base import Base


class ProposalState(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.UUID
    )
    document: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_version_id", ondelete="SET NULL")
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
        DateTime(timezone=True), insert_default=func.now(), nullable=True
    )
