import uuid
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.core.comments.models import CommentORM
from src.core.comments.schemas import CommentResponse
from src.core.contributions import ContributionORM
from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState, DocumentVisibility
from src.core.proposals.models import ProposalORM, ProposalState
from src.core.proposals.schemas import ProposalList, ProposalResponse
from src.core.versions.diff import compute_diff

COMMENTS_PAGE_SIZE = 20

from ...db.dependency import session
from ...exceptions import (
    DocumentNotFound,
    DocumentPermissionDenied,
    InvalidDocumentState,
    InvalidProposalState,
    ProposalNotFound,
)
from ..versions import VersionORM


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
        result = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFound()
        return proposal

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
        contribution = result.scalar_one_or_none()
        return contribution is not None

    async def _attach_comment_counts(self, proposals: list[ProposalORM]) -> None:
        if not proposals:
            return
        proposal_ids = [p.id for p in proposals]
        result = await self.session.execute(
            select(
                CommentORM.proposal_id,
                func.count(CommentORM.id),
                func.count(CommentORM.id).filter(CommentORM.resolved.is_(True)),
            )
            .where(CommentORM.proposal_id.in_(proposal_ids))
            .group_by(CommentORM.proposal_id)
        )
        counts = {row[0]: (row[1], row[2]) for row in result.all()}
        for proposal in proposals:
            total, resolved = counts.get(proposal.id, (0, 0))
            proposal.comment_count = total
            proposal.resolved_count = resolved

    def _diff_against_base(self, proposal: ProposalORM) -> tuple[list[dict], int, int]:
        base_content = proposal.base_version.content if proposal.base_version else ""
        return compute_diff(base_content, proposal.content)

    async def _first_comment_page(self, proposal_id: uuid.UUID) -> list[CommentResponse]:
        result = await self.session.execute(
            select(CommentORM)
            .where(CommentORM.proposal_id == proposal_id)
            .order_by(CommentORM.created_at)
            .limit(COMMENTS_PAGE_SIZE)
        )
        comments = list(result.scalars().all())
        return [CommentResponse.from_comment(c) for c in comments]

    async def create_proposal(
        self,
        document_id: uuid.UUID,
        actor: User,
        content: str,
        title: str,
        description: str | None = None,
    ) -> ProposalResponse:
        if not content.strip():
            raise ValueError("Proposal content cannot be empty")
        document = await self._get_document(document_id=document_id)

        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("cannot propose change to arhcived document")
        is_contributor = await self._is_active_contributor(
            document_id=document_id, user_id=actor.id
        )
        if not is_contributor:
            raise DocumentPermissionDenied("Only Contributors may create proposals")

        base_version_id = document.draft_version_id or document.published_version_id
        base_version = next(
            (v for v in document.versions if v.id == base_version_id), None
        )

        proposal = ProposalORM(
            document_id=document_id,
            author_id=actor.id,
            base_version_id=base_version_id,
            title=title,
            description=description,
            content=content,
            state=ProposalState.OPEN,
        )
        proposal.author = actor
        proposal.base_version = base_version

        self.session.add(proposal)
        await self.session.flush()
        await self.session.commit()

        # A brand new proposal has no comments yet.
        proposal.comment_count = 0
        proposal.resolved_count = 0

        lines, additions, deletions = self._diff_against_base(proposal)
        return ProposalResponse.from_proposal(
            proposal,
            author_name=actor.username,
            additions=additions,
            deletions=deletions,
            lines=lines,
        )

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
        await self.session.commit()

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
        await self.session.commit()

    async def accept_proposal(
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
        proposal.decided_at = dt.now(timezone.utc)
        await self.session.commit()

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
        proposal.decided_at = dt.now(timezone.utc)

        if reason:
            rejection_comment = CommentORM(
                proposal_id=proposal.id,
                author_id=actor_id,
                text=f"Rejected: {reason}",
            )
            self.session.add(rejection_comment)

        await self.session.commit()

    async def get_proposal(
        self, proposal_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProposalResponse:
        result = await self.session.execute(
            select(ProposalORM)
            .where(ProposalORM.id == proposal_id)
            .options(selectinload(ProposalORM.base_version))
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
        is_public = document.visibility == DocumentVisibility.PUBLIC
        if not (is_owner or is_author or is_contributor or is_public):
            raise DocumentPermissionDenied()
        await self._attach_comment_counts([proposal])
        comments = await self._first_comment_page(proposal.id)

        lines, additions, deletions = self._diff_against_base(proposal)
        return ProposalResponse.from_proposal(
            proposal,
            author_name=proposal.author.username,
            additions=additions,
            deletions=deletions,
            lines=lines,
            comments=comments,
        )

    async def list_proposals(
        self, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[ProposalList]:
        document = await self._get_document(document_id=document_id)
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot read archived docs")
        is_owner = document.owner_id == actor_id
        is_contributor = await self._is_active_contributor(
            document_id=document_id, user_id=actor_id
        )
        is_public = document.visibility == DocumentVisibility.PUBLIC
        if not (is_owner or is_contributor or is_public):
            raise DocumentPermissionDenied()

        result = await self.session.execute(
            select(ProposalORM)
            .where(ProposalORM.document_id == document_id)
            .order_by(desc(ProposalORM.created_at))
            .options(selectinload(ProposalORM.base_version))
        )
        proposals = list(result.scalars().all())
        await self._attach_comment_counts(proposals)

        responses = []
        for proposal in proposals:
            lines, additions, deletions = self._diff_against_base(proposal)
            responses.append(
                ProposalList.from_proposal(
                    proposal,
                    author_name=proposal.author.username,
                    additions=additions,
                    deletions=deletions,
                    lines=lines,
                )
            )
        return responses

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
        if document.state in (DocumentState.ARCHIVED, DocumentState.LOCKED):
            raise InvalidDocumentState("Cannot merge document with current state")

        # create the new merged version
        merged_version = VersionORM(
            document_id=document.id,
            author_id=actor_id,
            content=proposal.content,
            label=f"v{len(document.versions) + 1}",
            message=proposal.title,
        )
        self.session.add(merged_version)
        await self.session.flush()

        # mark and switch pointer
        document.draft_version_id = merged_version.id
        proposal.merged_at = dt.now(timezone.utc)

        # merging closes the discussion - resolve any comments still open
        open_comments = await self.session.execute(
            select(CommentORM).where(
                CommentORM.proposal_id == proposal.id,
                CommentORM.resolved.is_(False),
            )
        )
        now = dt.now(timezone.utc)
        for comment in open_comments.scalars().all():
            comment.resolved = True
            comment.resolved_at = now
            comment.resolved_by = actor_id

        await self.session.commit()

        return merged_version
