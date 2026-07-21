from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from .utils import compute_author_color, compute_initials

if TYPE_CHECKING:
    from .models import CommentORM


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    inline: bool = False
    line_number: int | None = None
    parent_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _validate_inline_line_number(self) -> "CommentCreate":
        if self.inline and self.line_number is None:
            raise ValueError("line_number is required when inline is true")
        return self


class CommentUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    resolved: bool | None = None


class CommentResponse(BaseModel):
    id: uuid.UUID
    proposal_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_initials: str
    author_color: str
    text: str
    created_at: datetime
    updated_at: datetime
    resolved: bool
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    inline: bool
    line_number: int | None
    parent_id: uuid.UUID | None

    @classmethod
    def from_comment(cls, comment: "CommentORM") -> "CommentResponse":
        return cls(
            id=comment.id,
            proposal_id=comment.proposal_id,
            author_id=comment.author_id,
            author_name=comment.author.username,
            author_initials=compute_initials(comment.author.username),
            author_color=compute_author_color(comment.author_id),
            text=comment.text,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            resolved=comment.resolved,
            resolved_at=comment.resolved_at,
            resolved_by=comment.resolved_by,
            inline=comment.inline,
            line_number=comment.line_number,
            parent_id=comment.parent_id,
        )


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
    resolved_count: int
