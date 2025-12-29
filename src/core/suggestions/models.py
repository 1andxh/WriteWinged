import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text
from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
from enum import Enum
from datetime import datetime


class Status(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Suggestion(SQLModel, table=True):
    __tablename__: str = "Suggestions"

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False)
    )
    document_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="documents.id", nullable=False
    )
    base_version_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="versions.id", nullable=False
    )
    author_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", nullable=False
    )

    content: str = Field(sa_column=Column(Text(), nullable=False))
    status: Status = Field(
        sa_column=Column(
            SAEnum(Status, name="status_enum", native_enum=False),
            nullable=False,
            server_default=Status.PENDING.value,
        )
    )
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
