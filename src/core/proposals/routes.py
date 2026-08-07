from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.proposals.models import ProposalState
from src.exceptions import ProposalNotFound

from .dependency import get_proposal_service
from .schemas import ProposalCreate, ProposalList, ProposalResponse, UpdateProposalState
from .services import ProposalService

proposal_router = APIRouter()
user = Annotated[User, Depends(get_current_user)]
proposal_service = Annotated[ProposalService, Depends(get_proposal_service)]


@proposal_router.post(
    "/{document_id}/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal(
    document_id: UUID,
    payload: ProposalCreate,
    current_user: user,
    service: proposal_service,
    background_tasks: BackgroundTasks,
):
    proposal = await service.create_proposal(
        document_id=document_id,
        actor_id=current_user.id,
        content=payload.content,
        title=payload.title,
        description=payload.description,
        background_tasks=background_tasks,
    )
    return proposal


@proposal_router.get(
    "/{document_id}/proposals",
    response_model=list[ProposalList],
)
async def list_proposals(
    document_id: UUID, current_user: user, service: proposal_service
):
    return await service.list_proposals(
        document_id=document_id, actor_id=current_user.id
    )


@proposal_router.get(
    "/{document_id}/proposals/{proposal_id}", response_model=ProposalResponse
)
async def get_proposal(
    document_id: UUID,
    proposal_id: UUID,
    current_user: user,
    service: proposal_service,
):
    proposal = await service.get_proposal(
        proposal_id=proposal_id, actor_id=current_user.id
    )
    if proposal.document_id != document_id:
        raise ProposalNotFound()
    return proposal


@proposal_router.patch("/{document_id}/proposals/{proposal_id}/state", status_code=204)
async def update_proposal_state(
    document_id: UUID,
    proposal_id: UUID,
    payload: UpdateProposalState,
    current_user: user,
    service: proposal_service,
) -> None:
    proposal = await service.get_proposal(
        proposal_id=proposal_id, actor_id=current_user.id
    )
    if proposal.document_id != document_id:
        raise ProposalNotFound()
    if payload.state == ProposalState.ACCEPTED:
        await service.accept_proposal(proposal_id=proposal_id, actor_id=current_user.id)
        return
    await service.reject_proposal(proposal_id=proposal_id, actor_id=current_user.id)
    return


@proposal_router.post(
    "/{document_id}/proposals/{proposal_id}/merge",
    response_model=ProposalResponse,
)
async def merge_proposal(
    document_id: UUID,
    proposal_id: UUID,
    current_user: user,
    service: proposal_service,
):
    proposal = await service.get_proposal(
        proposal_id=proposal_id, actor_id=current_user.id
    )
    if proposal.document_id != document_id:
        raise ProposalNotFound()
    await service.merge_proposal(proposal_id=proposal_id, actor_id=current_user.id)
    return await service.get_proposal(proposal_id=proposal_id, actor_id=current_user.id)
