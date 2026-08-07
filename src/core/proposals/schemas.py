from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.comments.utils import compute_author_color, compute_initials
from src.core.proposals.models import ProposalState
from src.core.versions.schemas import DiffLineOut

if TYPE_CHECKING:
    from .models import ProposalORM


class ProposalCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    content: str = Field(min_length=1)


class ProposalResponse(BaseModel):
    id: UUID
    document_id: UUID
    author_id: UUID
    author_name: str
    author_initials: str
    author_color: str
    title: str | None
    description: str | None
    state: ProposalState
    content: str
    created_at: datetime
    merged_at: datetime | None
    comment_count: int = 0
    resolved_count: int = 0
    additions: int
    deletions: int
    lines: list[DiffLineOut]

    @classmethod
    def from_proposal(
        cls,
        proposal: "ProposalORM",
        *,
        author_name: str,
        additions: int,
        deletions: int,
        lines: list[dict],
    ) -> "ProposalResponse":
        return cls(
            id=proposal.id,
            document_id=proposal.document_id,
            author_id=proposal.author_id,
            author_name=author_name,
            author_initials=compute_initials(author_name),
            author_color=compute_author_color(proposal.author_id),
            title=proposal.title,
            description=proposal.description,
            state=proposal.state,
            content=proposal.content,
            created_at=proposal.created_at,
            merged_at=proposal.merged_at,
            comment_count=proposal.comment_count,
            resolved_count=proposal.resolved_count,
            additions=additions,
            deletions=deletions,
            lines=lines,
        )


class ProposalList(ProposalResponse):
    pass


class UpdateProposalState(BaseModel):
    state: Literal[ProposalState.ACCEPTED, ProposalState.REJECTED]
