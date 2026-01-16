import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, Enum as SAEnum, String, Text, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from typing import Optional
from datetime import datetime, timezone
from ...db.base import Base


# class Version(SQLModel, table=True):
#     __tablename__: str = "versions"

#     id: uuid.UUID = Field(
#         sa_column=Column(
#             pg.UUID, primary_key=True, default=uuid.uuid4, nullable=False, index=True
#         )
#     )
#     document_id: Optional[uuid.UUID] = Field(
#         default=None, foreign_key="documents.id", nullable=False, index=True
#     )
#     author_id: Optional[uuid.UUID]
#     content: str
#     created_at: datetime = Field(
#         sa_column=Column(
#             DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
#         )
#     )


class VersionORM(Base):
    __tablename__ = "versions"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        default=None, nullable=False, index=True
    )
    content: Mapped[str]
