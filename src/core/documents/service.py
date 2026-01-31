from ...db.dependency import session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from .models import DocumentORM, DocumentState, DocumentVisibility
from ...exceptions import (
    DocumentPermissionDenied,
    DocumentNotFound,
    DocumentNotMutable,
    DocumentTitleConflict,
    InvalidDocumentState,
)
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
import uuid

now = datetime.now(timezone.utc)


class DocumentService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _can_manage(self, document: DocumentORM, actor_id) -> bool:

        return actor_id == document.owner_id

    def _ensure_mutable(self, document: DocumentORM):
        if document.deleted_at is not None:
            raise DocumentNotMutable("Document is deleted")

        if document.state == DocumentState.ARCHIVED:
            raise DocumentNotMutable("Unarchive the document to make changes.")

        if document.state == DocumentState.LOCKED:
            raise DocumentNotMutable("Unlock the document to make changes.")

        if document.state != DocumentState.ACTIVE:
            raise DocumentNotMutable(
                f"Document is not mutable in '{document.state}' state"
            )

    async def get_all_documents(
        self,
        actor_id: uuid.UUID,
        search_query: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DocumentORM]:
        statement = select(DocumentORM).where(
            DocumentORM.owner_id == actor_id,
            DocumentORM.state.in_([DocumentState.ACTIVE, DocumentState.LOCKED]),
            DocumentORM.deleted_at.is_(None),
        )
        if search_query:
            statement = statement.where(DocumentORM.title.ilike(f"%{search_query}%"))

        statement = (
            statement.order_by(desc(DocumentORM.updated_at)).limit(limit).offset(offset)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_public_documents(
        self, search_query: str | None = None, limit: int = 10, offset: int = 0
    ) -> list[DocumentORM]:
        statement = select(DocumentORM).where(
            DocumentORM.visibility == DocumentVisibility.PUBLIC,
            DocumentORM.deleted_at.is_(None),
        )
        if search_query:
            statement = statement.where(DocumentORM.title.ilike(f"%{search_query}%"))

        statement = (
            statement.limit(limit).offset(offset).order_by(desc(DocumentORM.updated_at))
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_document(self, document_id) -> DocumentORM:
        statement = select(DocumentORM).where(
            DocumentORM.id == document_id, DocumentORM.deleted_at == None
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()
        return document

    async def get_archived_documents(
        self,
        actor_id: uuid.UUID,
        search_query: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DocumentORM]:
        statement = select(DocumentORM).where(
            DocumentORM.owner_id == actor_id,
            DocumentORM.state == DocumentState.ARCHIVED,
            # DocumentORM.deleted_at.is_(None),
        )
        if search_query:
            statement = statement.where(DocumentORM.title.ilike(f"%{search_query}%"))
        statement = (
            statement.order_by(desc(DocumentORM.updated_at)).limit(limit).offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_document(self, actor_id: uuid.UUID, title: str) -> DocumentORM:
        if not actor_id:
            raise DocumentPermissionDenied("Not allowed to create document")

        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Document cannot be created without a title")
        title = clean_title

        document = DocumentORM(
            owner_id=actor_id,
            title=title,
            state=DocumentState.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
        )

        self.session.add(document)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise DocumentTitleConflict()

        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def rename_document(
        self, actor_id: uuid.UUID, document_id: uuid.UUID, title: str
    ) -> DocumentORM | None:

        document = await self.get_document(document_id)
        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()

        self._ensure_mutable(document)

        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Title cannot be empty")

        document.title = clean_title

        try:
            await self.session.commit()
            await self.session.refresh(document)
        except IntegrityError:
            await self.session.rollback()
            raise DocumentTitleConflict()

        return document

    async def lock_document(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentORM:
        document = await self.get_document(document_id=document_id)
        if document is None:
            raise DocumentNotFound()

        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()
        if document.state == DocumentState.ARCHIVED:
            raise DocumentNotMutable("Cannot lock document in current state")
        if document.state == DocumentState.LOCKED:
            raise DocumentNotMutable("Document already locked")

        document.state = DocumentState.LOCKED
        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def unlock_document(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentORM:
        document = await self.get_document(document_id)
        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()
        if document.state == DocumentState.ARCHIVED:
            raise DocumentNotMutable("Archived documents cannot be unlock")
        if document.state == DocumentState.ACTIVE:
            return document
        document.state = DocumentState.ACTIVE
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def archive_document(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentORM:
        document = await self.get_document(document_id)
        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()
        if document.state == DocumentState.ARCHIVED:
            raise DocumentNotMutable("Document is already archived")
        document.state = DocumentState.ARCHIVED
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def unarchive_document(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DocumentORM:
        document = await self.get_document(document_id=document_id)
        if document.state == DocumentState.ACTIVE:
            return document
        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()

        document.state = DocumentState.ACTIVE
        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def delete_document(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        document = await self.get_document(document_id)

        if not self._can_manage(document, actor_id):
            raise DocumentPermissionDenied()

        document.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
