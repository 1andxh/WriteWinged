from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from src.core.comments.utils import compute_author_color, compute_initials

if TYPE_CHECKING:
    from src.auth.models import User
    from src.core.documents.models import DocumentORM

    from .models import ContributionORM, ContributionRequestORM


class AddContributorModel(BaseModel):
    email: str


class InviteSentResponse(BaseModel):
    message: str
    email: str


class InvitePreviewResponse(BaseModel):
    document_id: uuid.UUID
    document_title: str
    inviter_name: str
    invitee_email: str


class ListContributor(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    initials: str
    color: str
    role: str
    joined_at: datetime

    @classmethod
    def from_contribution(cls, contribution: "ContributionORM") -> "ListContributor":
        return cls(
            id=contribution.user_id,
            email=contribution.user.email,
            name=contribution.user.username,
            initials=compute_initials(contribution.user.username),
            color=compute_author_color(contribution.user_id),
            role="contributor",
            joined_at=contribution.created_at,
        )

    @classmethod
    def from_owner(cls, document: "DocumentORM", owner: "User") -> "ListContributor":
        return cls(
            id=document.owner_id,
            email=owner.email,
            name=owner.username,
            initials=compute_initials(owner.username),
            color=compute_author_color(document.owner_id),
            role="owner",
            joined_at=document.created_at,
        )


class ContributionRequestCreate(BaseModel):
    message: str | None = None


class ContributionRequestRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    requester_id: uuid.UUID
    email: str
    name: str
    initials: str
    color: str
    message: str | None
    created_at: datetime

    @classmethod
    def from_request(
        cls, request: "ContributionRequestORM"
    ) -> "ContributionRequestRead":
        return cls(
            id=request.id,
            document_id=request.document_id,
            requester_id=request.user_id,
            email=request.user.email,
            name=request.user.username,
            initials=compute_initials(request.user.username),
            color=compute_author_color(request.user_id),
            message=request.message,
            created_at=request.created_at,
        )
