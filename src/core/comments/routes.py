from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.auth.dependencies import get_current_user
from src.auth.models import User

from .dependency import get_comment_service
from .schemas import CommentCreate, CommentListResponse, CommentResponse, CommentUpdate
from .service import CommentService

comment_router = APIRouter()
user = Annotated[User, Depends(get_current_user)]
comment_service = Annotated[CommentService, Depends(get_comment_service)]


@comment_router.get(
    "/{document_id}/proposals/{proposal_id}/comments",
    response_model=CommentListResponse,
)
async def list_comments(
    document_id: UUID, proposal_id: UUID, current_user: user, service: comment_service
):
    return await service.list_comments(
        document_id=document_id, proposal_id=proposal_id, actor_id=current_user.id
    )


@comment_router.post(
    "/{document_id}/proposals/{proposal_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    document_id: UUID,
    proposal_id: UUID,
    payload: CommentCreate,
    current_user: user,
    service: comment_service,
):
    return await service.create_comment(
        document_id=document_id,
        proposal_id=proposal_id,
        actor=current_user,
        payload=payload,
    )


@comment_router.patch(
    "/{document_id}/proposals/{proposal_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment(
    document_id: UUID,
    proposal_id: UUID,
    comment_id: UUID,
    payload: CommentUpdate,
    current_user: user,
    service: comment_service,
):
    return await service.update_comment(
        document_id=document_id,
        proposal_id=proposal_id,
        comment_id=comment_id,
        actor_id=current_user.id,
        payload=payload,
    )


@comment_router.delete(
    "/{document_id}/proposals/{proposal_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    document_id: UUID,
    proposal_id: UUID,
    comment_id: UUID,
    current_user: user,
    service: comment_service,
) -> None:
    await service.delete_comment(
        document_id=document_id,
        proposal_id=proposal_id,
        comment_id=comment_id,
        actor_id=current_user.id,
    )
