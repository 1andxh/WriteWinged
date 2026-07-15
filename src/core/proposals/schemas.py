from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from src.core.proposals.models import ProposalState
from datetime import datetime
from typing import Literal


class ProposalCreate(BaseModel):
    content: str = Field(min_length=1)


class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    author_id: UUID
    state: ProposalState
    content: str
    created_at: datetime
    merged_at: datetime | None


class ProposalList(ProposalResponse):
    pass


class UpdateProposalState(BaseModel):
    state: Literal[ProposalState.ACCEPTED, ProposalState.REJECTED]
