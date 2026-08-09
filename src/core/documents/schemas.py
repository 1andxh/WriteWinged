from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from src.core.comments.utils import compute_author_color, compute_initials
from src.core.contributions.schemas import ListContributor
from src.core.versions.schemas import VersionRead

if TYPE_CHECKING:
    from src.auth.models import User
    from src.core.versions.models import VersionORM

    from .models import DocumentORM


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: str
    updated_at: datetime


class DocumentCreateRequest(BaseModel):
    title: str
    category: str | None = None


class DocumentRenameRequest(BaseModel):
    title: str


class DocumentReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    state: str
    owner_id: uuid.UUID
    visibility: str
    created_at: datetime
    updated_at: datetime
    published_version_id: uuid.UUID | None
    draft_version_id: uuid.UUID | None
    versions: list[VersionRead]
    contributions: list[ListContributor] = Field(default_factory=list)

    @field_validator("contributions", mode="before")
    @classmethod
    def _convert_contributions(cls, value):
        return [
            item
            if isinstance(item, ListContributor)
            else ListContributor.from_contribution(item)
            for item in value
        ]

    @computed_field
    @property
    def content(self) -> str:
        version_id = self.draft_version_id or self.published_version_id
        if version_id is None:
            return ""
        return next((v.content for v in self.versions if v.id == version_id), "")

    @computed_field
    @property
    def word_count(self) -> int:
        return len(self.content.split())


def _build_excerpt(content: str, limit: int = 200) -> str:
    text = " ".join(
        line.lstrip("#").strip() for line in content.splitlines() if line.strip()
    )
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


class PublicDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    excerpt: str
    content: str
    tag: str
    author_id: uuid.UUID
    author_name: str
    author_initials: str
    author_color: str
    published_at: datetime
    version: str
    word_count: int

    @classmethod
    def from_document(
        cls,
        document: "DocumentORM",
        owner: "User",
        published_version: "VersionORM",
    ) -> "PublicDocumentResponse":
        content = published_version.content
        return cls(
            id=document.id,
            title=document.title,
            excerpt=_build_excerpt(content),
            content=content,
            tag=document.category or "General",
            author_id=document.owner_id,
            author_name=owner.username,
            author_initials=compute_initials(owner.username),
            author_color=compute_author_color(document.owner_id),
            published_at=published_version.created_at,
            version=published_version.label or "",
            word_count=len(content.split()),
        )
