from fastapi import APIRouter, status, Depends
from ...auth.dependencies import get_current_user
from ...db.dependency import get_session
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Annotated
from src.auth.models import User
from .service import VersionService
from .dependency import get_version_service
from src.core.documents.routes import document_router
from .schemas import (
    VersionPublishRequest,
    VersionCreate,
    VersionCreateResponse,
    VersionRead,
)

version_router = APIRouter()
# version_router = document_router
user = Annotated[User, Depends(get_current_user)]
version_service = Annotated[VersionService, Depends(get_version_service)]


@version_router.post(
    "/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=VersionCreateResponse,
    tags=["versions"],
)
async def create_version(
    document_id: uuid.UUID,
    payload: VersionCreate,
    service: version_service,
    current_user: user,
):
    new_version = await service.create_version(
        author_id=current_user.id, document_id=document_id, content=payload.content
    )
    return new_version


@version_router.get(
    "/{document_id}/versions", response_model=list[VersionRead], tags=["versions"]
)
async def get_all_versions(
    document_id: uuid.UUID, service: version_service, current_user: user
):
    versions = await service.get_all_versions(
        document_id=document_id, actor_id=current_user.id
    )

    return versions


@version_router.get("/{document_id}/versions{version_id}", response_model=VersionRead)
async def get_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    service: version_service,
    current_user: user,
):
    version = await service.get_version(
        document_id=document_id, actor_id=current_user.id, version_id=version_id
    )
    return version


@version_router.post(
    "/{document_id}/publish",
    tags=["versions"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def publish_version(
    document_id: uuid.UUID,
    payload: VersionPublishRequest,
    service: version_service,
    current_user: user,
) -> None:
    await service.publish_version(
        document_id=document_id, version_id=payload.version_id, actor_id=current_user.id
    )
    return


@version_router.post(
    "/{document_id}/unpublish",
    tags=["versions"],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unpublish_version(
    document_id: uuid.UUID,
    service: version_service,
    current_user: user,
) -> None:
    await service.unpublish_version(document_id=document_id, actor_id=current_user.id)
    return
