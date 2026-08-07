import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.auth import User
from src.auth.dependencies import get_current_user
from src.exceptions import (
    ContributionAlreadyRevoked,
    ContributionNotFound,
    DocumentNotFound,
    DocumentPermissionDenied,
    WriteWingedException,
)

from .dependency import get_contribution_service
from .schemas import (
    AddContributorModel,
    InvitePreviewResponse,
    InviteSentResponse,
    ListContributor,
)
from .services import ContributionService

contributions_router = APIRouter()
invitation_router = APIRouter()
user = Annotated[User, Depends(get_current_user)]
contribution_service = Annotated[
    ContributionService, Depends(get_contribution_service)
]


@contributions_router.get(
    "/{document_id}/contributors",
    response_model=list[ListContributor],
)
async def get_contributors(
    document_id: uuid.UUID, current_user: user, service: contribution_service
):
    contributors = await service.list_contributors(
        document_id=document_id, actor_id=current_user.id
    )
    return contributors


@contributions_router.post(
    "/{document_id}/contributors",
    status_code=status.HTTP_200_OK,
    response_model=InviteSentResponse,
)
async def invite_contributor(
    document_id: uuid.UUID,
    payload: AddContributorModel,
    current_user: user,
    service: contribution_service,
    background_tasks: BackgroundTasks,
):
    try:
        return await service.invite_contributor(
            document_id=document_id,
            email=payload.email,
            actor_id=current_user.id,
            background_tasks=background_tasks,
        )
    except DocumentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    except DocumentPermissionDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permission to perform action",
        )
    except ValueError as e:
        raise WriteWingedException(str(e))


@invitation_router.get("/{token}", response_model=InvitePreviewResponse)
async def preview_invitation(
    token: str, current_user: user, service: contribution_service
):
    return await service.preview_invitation(token=token, actor=current_user)


@invitation_router.post("/{token}/accept", response_model=ListContributor)
async def accept_invitation(
    token: str, current_user: user, service: contribution_service
):
    return await service.accept_invitation(token=token, actor=current_user)


@contributions_router.delete(
    "/{document_id}/contributors/{contributor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_contributor(
    document_id: uuid.UUID,
    contributor_id: uuid.UUID,
    current_user: user,
    service: contribution_service,
):
    try:
        await service.revoke_contributor(
            document_id=document_id,
            contributor_id=contributor_id,
            actor_id=current_user.id,
        )
    except DocumentPermissionDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permission to perform action",
        )
    except ContributionNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found"
        )
    except ContributionAlreadyRevoked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Contribution already exists"
        )
    return
