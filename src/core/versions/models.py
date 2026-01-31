import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Enum as SAEnum, String, Text, DateTime, func, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime, timezone
from src.db.base import Base
from src.core.documents import DocumentORM
from src.auth.models import User


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
    # label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # change_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    # relationships
    document: Mapped["DocumentORM"] = relationship(
        back_populates="versions", foreign_keys=[document_id]
    )
    author: Mapped["User"] = relationship()
