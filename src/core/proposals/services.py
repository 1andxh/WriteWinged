from fastapi.exceptions import HTTPException
from fastapi import status
from ...db.dependency import session
from ...auth.models import User
from ..versions import VersionORM
import uuid
from src.core.documents import DocumentORM
from ...exceptions import DocumentNotFound, ContributionNotFound
from datetime import datetime as dt, timezone
from sqlalchemy import select
from src.core.contributions import ContributionORM

now = dt.now(timezone.utc)


class ProposalService:
    def __init__(self, session: session) -> None:
        self.session = session

    async def _get_document(self, document_id: uuid.UUID) -> DocumentORM:
        result = await self.session.execute(
            select(DocumentORM).where(DocumentORM.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()
        return document

    async def _is_active_contributor(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await self.session.execute(
            select(ContributionORM).where(
                ContributionORM.document_id == document_id,
                ContributionORM.user_id == user_id,
                ContributionORM.revoked_at.is_(None),
            )
        )
        if result is None:
            raise ContributionNotFound()
        return result.scalar_one_or_none()

    async def create_proposla(
        self,
    ):
        pass
