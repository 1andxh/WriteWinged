import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime, ForeignKey, func
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class DocumentVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class DocumentState(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    ARCHIVED = "archived"


class Base(DeclarativeBase):
    pass


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

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
    )

    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("versions.id", ondelete="SET NULL")
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
