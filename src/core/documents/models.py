import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime
import sqlalchemy.dialects.postgresql as pg


class DocumentVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class Document(SQLModel, table=True):
    __tablename__: str = "documents"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False, index=True
        )
    )
    owner_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", index=True
    )
    title: str = Field(
        sa_column_kwargs={"index": True, "max_length": 255, "nullable": False}
    )
    visibility: DocumentVisibility = Field(
        sa_column=Column(
            SAEnum(DocumentVisibility, name="visibility_enum", native_enum=False),
            server_default=DocumentVisibility.PUBLIC.value,
            nullable=False,
        )
    )
    is_archived: bool = Field(default=False)
    current_version_id: Optional[uuid.UUID]
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )
    )
