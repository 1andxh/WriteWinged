from fastapi import APIRouter, Depends
from .schemas import ProposalResponse, ProposalCreate, UpdateProposalState, ProposalList
from uuid import UUID
from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.db.dependency import get_session
from typing import Annotated
from .services import ProposalService


proposal_router = APIRouter()
user = Annotated[User, Depends(get_current_user)]


@proposal_router.post("/{document_id}/proposls", response_model=ProposalResponse)
async def create_proposal(
    document_id: UUID,
    payload: ProposalCreate,
    current_user: user,
    service: ProposalService,
):
    proposal = await service.create_proposal(
        document_id=document_id, actor_id=current_user.id, content=payload.content
    )
    return proposal


@proposal_router.get(
    "/{document_id}/proposals",
    response_model=list[ProposalList],
)
async def list_proposals(
    documenr_id: UUID, current_user: user, serivice: ProposalService
):
    return await serivice.list_proposals(
        document_id=documenr_id, actor_id=current_user.id
    )


@proposal_router.get("/{document_id}/proposals/{proposal_id}")
async def get_proposal():
    pass


@proposal_router.patch("/{document_id}/proposals/{proposal_id}/state")
async def update_proposal_state():
    pass


@proposal_router.post("/{document_id}/proposals/{proposal_id}/merge")
async def merge_proposal():
    pass
