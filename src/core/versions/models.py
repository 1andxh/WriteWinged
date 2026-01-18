import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Enum as SAEnum, String, Text, DateTime, func, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from typing import Optional
from datetime import datetime, timezone
from ...db.base import Base
from ..documents.models import DocumentORM
from ...auth.models import User


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
    document_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    # relationships
    document: Mapped["DocumentORM"] = relationship(
        back_populates="versions", foreign_keys=[document_id]
    )
    author: Mapped["User"] = relationship()
