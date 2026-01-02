import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime
from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
from datetime import datetime, timezone


class Version(SQLModel, table=True):
    __tablename__: str = "versions"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False, index=True
        )
    )
    document_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="documents.id", nullable=False, index=True
    )
    author_id: Optional[uuid.UUID]
    content: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )
    )
