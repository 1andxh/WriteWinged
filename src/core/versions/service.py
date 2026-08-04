import uuid

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.documents import DocumentORM
from src.core.documents.models import DocumentVisibility
from src.core.versions import VersionORM
from src.core.versions.diff import compute_diff
from src.core.versions.schemas import VersionDiffResponse, VersionRead
from src.core.versions.utils import (
    can_author_version,
    can_publish_version,
    ensure_version_belongs,
)
from src.exceptions import (
    DocumentNotFound,
    DocumentPermissionDenied,
    VersionDoesNotExist,
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
        self,
        *,
        author_id: uuid.UUID,
        document_id: uuid.UUID,
        content: str,
        message: str | None = None,
    ) -> VersionORM:
        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()

        self._ensure_can_modify(document, author_id)

        can_author_version(document)

        version = VersionORM(
            document_id=document_id,
            author_id=author_id,
            content=content,
            label=f"v{len(document.versions) + 1}",
            message=message,
        )
        self.session.add(version)
        await self.session.flush()

        document.draft_version_id = version.id
        self.session.add(document)
        await self.session.commit()

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

        await self.session.commit()

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
        await self.session.commit()

    async def _versions_with_stats(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> tuple[DocumentORM, list[VersionORM], list[VersionRead]]:
        document_result = await self.session.execute(
            select(DocumentORM).where(DocumentORM.id == document_id)
        )
        document = document_result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()

        if document.visibility == DocumentVisibility.PRIVATE:
            self._ensure_can_modify(document, actor_id)

        statement = (
            select(VersionORM)
            .where(VersionORM.document_id == document_id)
            .order_by(asc(VersionORM.created_at))
            .options(selectinload(VersionORM.author))
        )
        result = await self.session.execute(statement)
        versions = list(result.scalars().all())

        reads: list[VersionRead] = []
        previous_content = ""
        for version in versions:
            _, additions, deletions = compute_diff(previous_content, version.content)
            reads.append(
                VersionRead.from_version(
                    version,
                    published=version.id == document.published_version_id,
                    additions=additions,
                    deletions=deletions,
                )
            )
            previous_content = version.content

        return document, versions, reads

    async def get_version(
        self, document_id: uuid.UUID, actor_id, version_id: uuid.UUID | None = None
    ) -> VersionRead:
        _, _, reads = await self._versions_with_stats(document_id, actor_id)
        for read in reads:
            if read.id == version_id:
                return read
        raise VersionDoesNotExist()

    async def get_all_versions(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[VersionRead]:
        _, _, reads = await self._versions_with_stats(document_id, actor_id)
        return reads

    async def get_version_diff(
        self, document_id: uuid.UUID, version_id: uuid.UUID, actor_id: uuid.UUID
    ) -> VersionDiffResponse:
        _, versions, _ = await self._versions_with_stats(document_id, actor_id)

        index = next((i for i, v in enumerate(versions) if v.id == version_id), None)
        if index is None:
            raise VersionDoesNotExist()

        version = versions[index]
        previous = versions[index - 1] if index > 0 else None
        previous_content = previous.content if previous else ""

        lines, additions, deletions = compute_diff(previous_content, version.content)
        title = (
            f"{previous.label} → {version.label}"
            if previous
            else f"{version.label} (initial)"
        )

        return VersionDiffResponse(
            title=title, additions=additions, deletions=deletions, lines=lines
        )
