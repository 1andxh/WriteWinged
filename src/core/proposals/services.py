from fastapi.exceptions import HTTPException
from fastapi import status
from ...db.dependency import session
from ...auth.models import User
from ..versions import VersionORM
import uuid
from src.core.documents import DocumentORM
from ...exceptions import (
    DocumentNotFound,
    ContributionNotFound,
    InvalidDocumentState,
    DocumentPermissionDenied,
    ProposalNotFound,
    InvalidProposalState,
)
from datetime import datetime as dt, timezone
from sqlalchemy import select
from src.core.contributions import ContributionORM
from src.core.documents.models import DocumentState
from src.core.proposals.models import ProposalORM, ProposalState

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

    async def create_proposal(
        self,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
        content: str,
        base_version_id: uuid.UUID | None = None,
    ):
        if not content.strip():
            raise ValueError("Proposal content cannot be empty")
        document = await self._get_document(document_id=document_id)

        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("cannot propose change to arhcived document")
        is_contributor = await self._is_active_contributor(
            document_id=document_id, user_id=actor_id
        )
        if not is_contributor:
            raise DocumentPermissionDenied("Only Contributors may create proposals")
        proposal = ProposalORM(
            document_id=document_id,
            author_id=actor_id,
            base_version_id=base_version_id,
            content=content,
            state=ProposalState.OPEN,
        )

        self.session.add(proposal)
        await self.session.flush()

        return proposal

    async def update_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID, content: str
    ) -> None:
        if not content.strip():
            raise ValueError("Proposal content cannot be empty")

        result = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()

        if proposal is None:
            raise ProposalNotFound()
        if proposal.state != ProposalState.OPEN:
            raise InvalidProposalState()
        if proposal.author_id != actor_id:
            raise DocumentPermissionDenied()

        proposal.content = content
