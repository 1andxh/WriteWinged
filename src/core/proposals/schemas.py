from pydantic import BaseModel, Field
from uuid import UUID
from src.core.proposals.models import ProposalState
from datetime import datetime


class ProposalCreate(BaseModel):
    content: str = Field(min_length=1)


class ProposalResponse(BaseModel):
    id: UUID
    document_id: UUID
    author_id: UUID
    state: ProposalState
    content: str
    created_at: datetime
    merged_at: datetime | None

    class Config:
        from_attributes = True


class ProposalList(ProposalResponse):
    pass
