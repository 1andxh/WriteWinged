# from src.db.dependency import session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.core.documents import DocumentORM
from src.core.versions import VersionORM
import uuid
from src.core.versions.utils import can_author_version, can_publish_version
from src.exceptions import VersionDoesNotExist


class VersionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_version(
        self, *, author_id: uuid.UUID, document_id: uuid.UUID, content: str
    ) -> VersionORM:

        async with self.session.begin():
            statement = (
                select(DocumentORM)
                .where(DocumentORM.id == document_id)
                .with_for_update()
            )
        result = await self.session.execute(statement)
        document = result.scalar_one()

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
        self, *, document_id: uuid.UUID, version_id: uuid.UUID
    ) -> None:
        async with self.session.begin():
            statement = (
                select(DocumentORM)
                .where(DocumentORM.id == document_id)
                .with_for_update()
            )
            result = await self.session.execute(statement)
            document = result.scalar_one_or_none()

            can_publish_version(document)

            version_to_publish = select(VersionORM).where(VersionORM.id == version_id)
            version_result = await self.session.execute(version_to_publish)
            version = version_result.scalar_one_or_none()

            if version is None:
                pass

    async def unpublish_version(self, document_id: uuid.UUID):
        pass
