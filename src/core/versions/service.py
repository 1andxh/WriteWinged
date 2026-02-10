# from src.db.dependency import session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc
from src.core.documents import DocumentORM
from src.core.documents.models import DocumentVisibility
from src.core.versions import VersionORM
import uuid
from src.core.versions.utils import (
    can_author_version,
    can_publish_version,
    ensure_version_belongs,
)
from src.exceptions import (
    VersionDoesNotExist,
    DocumentNotFound,
    DocumentNotMutable,
    DocumentPermissionDenied,
)


class VersionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    def _ensure_can_modify(self, document: DocumentORM, author_id: uuid.UUID):
        if document.owner_id != author_id:
            raise DocumentPermissionDenied()

    async def create_version(
        self, *, author_id: uuid.UUID, document_id: uuid.UUID, content: str
    ) -> VersionORM:
        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one()

        self._ensure_can_modify(document, author_id)

        can_author_version(document)

        version = VersionORM(
            document_id=document_id,
            author_id=author_id,
            content=content,
        )
        self.session.add(version)
        await self.session.flush()

        document.draft_version_id = version.id
        self.session.add(document)

        return version

    async def publish_version(
        self, *, document_id: uuid.UUID, version_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()
        self._ensure_can_modify(document, actor_id)

        can_publish_version(document)

        version_to_publish = select(VersionORM).where(VersionORM.id == version_id)
        version_result = await self.session.execute(version_to_publish)
        version = version_result.scalar_one_or_none()

        if version is None:
            raise VersionDoesNotExist()
        ensure_version_belongs(version, document_id)

        # pointer swap
        document.published_version_id = version.id

        # clear draft pointer
        if document.draft_version_id == version.id:
            document.draft_version_id = None

    async def unpublish_version(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:

        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()
        self._ensure_can_modify(document, actor_id)
        can_publish_version(document)

        if document.published_version_id is None:
            return
        document.published_version_id = None

    async def get_version(
        self, document_id: uuid.UUID, actor_id, version_id: uuid.UUID | None = None
    ) -> VersionORM:
        statement = select(VersionORM).where(
            VersionORM.id == version_id, VersionORM.document_id == document_id
        )
        result = await self.session.execute(statement)
        version = result.scalar_one_or_none()
        if version is None:
            raise VersionDoesNotExist("")
        document = version.document
        if document.visibility == DocumentVisibility.PRIVATE:
            self._ensure_can_modify(document, actor_id)

        return version

    async def get_all_versions(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[VersionORM]:
        statement = (
            select(VersionORM)
            .where(VersionORM.document_id == document_id)
            .order_by(asc(VersionORM.created_at))
        )
        result = await self.session.execute(statement)
        versions = list(result.scalars().all())

        # todo: load all versions for document

        # if document.visibility == DocumentVisibility.PRIVATE:
        #     self._ensure_can_modify(document, actor_id)
        return versions
