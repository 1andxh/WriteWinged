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
    ProposalAlreadyMerged,
)
from datetime import datetime as dt, timezone
from sqlalchemy import select, desc
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

    async def _get_proposal(self, proposal_id: uuid.UUID):
        pass

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

    async def withdraw_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        stmt = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = stmt.scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFound()
        if proposal.state != ProposalState.OPEN:
            raise InvalidProposalState("Only open proposals can be withdrawn")
        if proposal.author_id != actor_id:
            raise DocumentPermissionDenied()

        proposal.state = ProposalState.WITHDRAWN

    async def accept_propopsal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        stmt = await self.session.execute(
            select(ProposalORM)
            .join(DocumentORM, ProposalORM.document_id == DocumentORM.id)
            .where(ProposalORM.id == proposal_id)
        )
        proposal = stmt.scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFound()

        document = await self._get_document(document_id=proposal.document_id)

        if document.owner_id != actor_id:
            raise DocumentPermissionDenied()
        if proposal.state != ProposalState.OPEN:
            raise InvalidProposalState("Only open proposals can be accepted")

        proposal.state = ProposalState.ACCEPTED
        proposal.decided_at = now

    async def reject_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID, reason: str | None = None
    ) -> None:
        result = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFound()
        document = await self._get_document(document_id=proposal.document_id)
        if document.owner_id != actor_id:
            raise DocumentPermissionDenied()
        if proposal.state != ProposalState.OPEN:
            raise InvalidProposalState("Only open proposals can be rejected")

        proposal.state = ProposalState.REJECTED
        proposal.decided_at = now

    async def get_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProposalORM:
        result = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFound()
        document = await self._get_document(document_id=proposal.document_id)
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot read archived docs")
        is_owner = document.owner_id == actor_id
        is_author = proposal.author_id == actor_id
        is_contributor = await self._is_active_contributor(
            document_id=proposal.document_id, user_id=actor_id
        )
        if not (is_owner or is_author or is_contributor):
            raise DocumentPermissionDenied()
        return proposal

    async def list_proposals(self, document_id: uuid.UUID, actor_id: uuid.UUID):
        document = await self._get_document(document_id=document_id)
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot read archived docs")
        is_owner = document.owner_id == actor_id
        is_contributor = await self._is_active_contributor(
            document_id=document_id, user_id=actor_id
        )
        if not (is_owner or is_contributor):
            raise DocumentPermissionDenied()

        proposals = await self.session.execute(
            select(ProposalORM)
            .where(ProposalORM.document_id == document_id)
            .order_by(desc(ProposalORM.created_at))
        )
        return proposals.scalars().all()

    async def merge_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID
    ) -> VersionORM:
        # lock porposla
        result = await self.session.execute(
            select(ProposalORM)
            .where(ProposalORM.id == proposal_id, ProposalORM.merged_at.is_(None))
            .with_for_update()
        )
        proposal = result.scalar_one_or_none()

        if proposal is None:
            raise ProposalNotFound()
        if proposal.state != ProposalState.ACCEPTED:
            raise InvalidProposalState("Cannot merge proposal")
        # if proposal.merged_at is not None:
        #     raise ProposalAlreadyMerged()

        # lock the document
        result = await self.session.execute(
            select(DocumentORM)
            .where(DocumentORM.id == proposal.document_id)
            .with_for_update()
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()
        if document.owner_id != actor_id:
            raise DocumentPermissionDenied()
        if document.state in (DocumentState.ARCHIVED or DocumentState.LOCKED):
            raise InvalidDocumentState("Cannot merge document with current state")

        # create the new merged version
        merged_version = VersionORM(
            document_id=document.id,
            author_id=actor_id,
            content=proposal.content,
        )
        self.session.add(merged_version)
        await self.session.flush()

        # mark and switch pointer
        document.draft_version_id = merged_version.id
        proposal.merged_at = now

        return merged_version
