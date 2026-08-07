import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.auth.models import User

from ...auth.dependencies import get_current_user
from .dependency import get_version_service
from .schemas import (
    VersionCreate,
    VersionCreateResponse,
    VersionDiffResponse,
    VersionPublishRequest,
    VersionRead,
)
from .service import VersionService

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
        author_id=current_user.id,
        document_id=document_id,
        content=payload.content,
        message=payload.message,
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


@version_router.get(
    "/{document_id}/versions/{version_id}", response_model=VersionRead
)
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


@version_router.get(
    "/{document_id}/versions/{version_id}/diff",
    response_model=VersionDiffResponse,
    tags=["versions"],
)
async def get_version_diff(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    service: version_service,
    current_user: user,
):
    return await service.get_version_diff(
        document_id=document_id, version_id=version_id, actor_id=current_user.id
    )


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
