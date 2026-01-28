from fastapi import Depends
from .models import DocumentORM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.dependency import session
import uuid
from src.core.documents.service import DocumentService
from src.core.documents.dependency import get_document_service
from src.exceptions import (
    DocumentNotFound,
    DocumentPermissionDenied,
    ContributionAlreadyExists,
    InvalidContributionTarget,
)
from .models import ContributionORM
from datetime import datetime, timezone
from typing import Annotated

now = datetime.now(timezone.utc)
# doc_service = DocumentService(self.session)
# nts: borrowing another class? just add to __init__ and create an instance


class ContributionService:
    def __init__(self, session: session) -> None:
        self.session = session
        self.doc_service = DocumentService(session)

    def _is_owner(self, actor_id: uuid.UUID, document: DocumentORM):
        if document.id != actor_id:
            raise DocumentPermissionDenied()

    async def add_contributor(
        self, document_id: uuid.UUID, contributor_id: uuid.UUID, actor_id: uuid.UUID
    ):
        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()

        self._is_owner(actor_id=actor_id, document=document)
        if contributor_id == document.owner_id:
            raise InvalidContributionTarget()

        existing_contribution = select(ContributionORM).where(
            ContributionORM.document_id == document_id,
            ContributionORM.user_id == contributor_id,
        )
        if existing_contribution is None:
            raise ContributionAlreadyExists()

        contribution = ContributionORM(
            document_id=document.id,
            user_id=contributor_id,
            created_at=now,
            revoked_at=None,
        )
        self.session.add(contribution)
        await self.session.flush()
        return contribution

    async def revoke_contributor(
        self,
        document_id: uuid.UUID,
        contributor_id: uuid.UUID,
        actor_id: uuid.UUID,
        for_update: bool = False,
    ):

        document = await self.doc_service.get_document(
            document_id=document_id
        )  # lock this?
