from src.db.base import Base
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func, ForeignKey, UniqueConstraint
import uuid
from datetime import datetime
from src.core.documents import DocumentORM
from src.auth import User


class ContributionORM(Base):
    __tablename__ = "contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_At: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    document: Mapped["DocumentORM"] = relationship(
        back_populates="contributions", lazy="selectin"
    )
    user: Mapped["User"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "document_id", "user_id", name="uq_contribution_document_user"
        ),
    )
