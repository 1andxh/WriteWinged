from fastapi import APIRouter, Depends, status, Query
from .schemas import (
    DocumentResponse,
    DocumentCreateRequest,
    DocumentReadResponse,
    DocumentRenameRequest,
)
from .service import DocumentService, DocumentVisibility
import uuid
from ...auth.dependencies import get_current_user
from ...auth.models import User
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from .dependency import get_document_service
from ...db.dependency import session
from ...exceptions import DocumentNotFound, DocumentPermissionDenied, DocumentNotMutable


document_router = APIRouter()
document_service = Annotated[DocumentService, Depends(get_document_service)]
user = Annotated[User, Depends(get_current_user)]


@document_router.get("/", response_model=list[DocumentReadResponse])
async def get_public_documents(
    service: document_service,
    q: str | None = Query(None, description="search documents by title"),
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
):
    documents = await service.list_public_documents(
        search_query=q, limit=limit, offset=offset
    )
    return documents


@document_router.get("/me", response_model=list[DocumentReadResponse])
async def list_user_documents(
    service: document_service,
    user: user,
    q: str | None = Query(None, description="search owned documents"),
    limit: int = Query(10, le=30),
    offset: int = Query(0, ge=0),
):
    documents = await service.get_all_documents(
        actor_id=user.id, search_query=q, limit=limit, offset=offset
    )
    return documents


@document_router.get("/{document_id}", response_model=DocumentReadResponse)
async def get_document(document_id: uuid.UUID, service: document_service, user: user):
    document = await service.get_document(document_id=document_id)
    if document.visibility == DocumentVisibility.PRIVATE:
        if document.owner_id != user.id:
            raise DocumentPermissionDenied()

    return document


@document_router.get("/archive", response_model=list[DocumentReadResponse])
async def get_archived_documents(
    service: document_service,
    user: user,
    q: str | None = Query(None, description="search owned documents"),
    limit: int = Query(10, le=30),
    offset: int = Query(0, ge=0),
):

    return await service.get_archived_documents(
        actor_id=user.id, search_query=q, limit=limit, offset=offset
    )


@document_router.post(
    "/", response_model=DocumentReadResponse, status_code=status.HTTP_201_CREATED
)
async def create_document(
    payload: DocumentCreateRequest, service: document_service, user: user
):
    new_document = await service.create_document(actor_id=user.id, title=payload.title)

    return new_document


@document_router.patch("/{document_id}/rename", response_model=DocumentResponse)
async def rename_document(
    document_id: uuid.UUID,
    payload: DocumentRenameRequest,
    service: document_service,
    user: user,
):
    updated_document = await service.rename_document(
        actor_id=user.id, document_id=document_id, title=payload.title
    )

    return updated_document


@document_router.post("/{document_id}/archive", response_model=DocumentResponse)
async def archive_document(
    document_id: uuid.UUID, service: document_service, user: user
):
    document = await service.archive_document(document_id=document_id, actor_id=user.id)
    return document


@document_router.delete("/{document_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID, service: document_service, user: user
):
    await service.delete_document(document_id=document_id, actor_id=user.id)
    return None


@document_router.post("/{document_id}/lock", response_model=DocumentResponse)
async def lock_document(
    document_id: uuid.UUID, service: document_service, user: user
):
    return await service.lock_document(document_id=document_id, actor_id=user.id)


@document_router.post("/{document_id}/unlock", response_model=DocumentReadResponse)
async def unlock_document(
    document_id: uuid.UUID, service: document_service, user: user
):
    return await service.unlock_document(document_id=document_id, actor_id=user.id)


@document_router.post("/{document_id}/unarchive", response_model=DocumentReadResponse)
async def unarchive_document(
    document_id: uuid.UUID, service: document_service, user: user
):
    return await service.unarchive_document(document_id=document_id, actor_id=user.id)
