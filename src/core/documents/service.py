# from ...db.dependency import session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import DocumentORM
from ...exceptions import DocumentNotFound


class DocumentService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_document(self, document_id) -> DocumentORM | None:
        statement = select(DocumentORM).where(
            DocumentORM.id == document_id, DocumentORM.deleted_at == None
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()
        return document

    # async def crea
