from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from .models import VersionORM


class VersionCreate(BaseModel):
    content: str
    message: str | None = None


class VersionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    author_id: uuid.UUID
    document_id: uuid.UUID
    label: str | None
    message: str | None


class VersionPublishRequest(BaseModel):
    version_id: uuid.UUID


class VersionRead(BaseModel):
    id: uuid.UUID
    content: str
    author_id: uuid.UUID
    author_name: str
    created_at: datetime
    label: str | None
    message: str | None
    published: bool
    additions: int
    deletions: int

    @classmethod
    def from_version(
        cls, version: "VersionORM", *, published: bool, additions: int, deletions: int
    ) -> "VersionRead":
        return cls(
            id=version.id,
            content=version.content,
            author_id=version.author_id,
            author_name=version.author.username,
            created_at=version.created_at,
            label=version.label,
            message=version.message,
            published=published,
            additions=additions,
            deletions=deletions,
        )


class DiffLineOut(BaseModel):
    t: str
    n: str | None
    text: str


class VersionDiffResponse(BaseModel):
    title: str
    additions: int
    deletions: int
    lines: list[DiffLineOut]
