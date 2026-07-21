import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from src.auth.models import User
from src.core.contributions import ContributionORM
from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState
from src.core.proposals.models import ProposalORM

from ...db.dependency import session
from ...exceptions import (
    CommentNotFound,
    DocumentNotFound,
    DocumentPermissionDenied,
    InvalidDocumentState,
    ProposalNotFound,
)
from .models import CommentORM
from .schemas import CommentCreate, CommentListResponse, CommentResponse, CommentUpdate


class CommentService:
    def __init__(self, session: session) -> None:
        self.session = session

    async def _get_proposal(
        self, document_id: uuid.UUID, proposal_id: uuid.UUID
    ) -> ProposalORM:
        result = await self.session.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None or proposal.document_id != document_id:
            raise ProposalNotFound()
        return proposal

    async def _get_document(self, document_id: uuid.UUID) -> DocumentORM:
        result = await self.session.execute(
            select(DocumentORM).where(DocumentORM.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()
        return document

    async def _get_comment(self, comment_id: uuid.UUID) -> CommentORM:
        result = await self.session.execute(
            select(CommentORM).where(CommentORM.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            raise CommentNotFound()
        return comment

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
        return result.scalar_one_or_none() is not None

    async def _ensure_can_view(
        self, document: DocumentORM, actor_id: uuid.UUID
    ) -> None:
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot read archived docs")
        is_owner = document.owner_id == actor_id
        is_contributor = await self._is_active_contributor(document.id, actor_id)
        if not (is_owner or is_contributor):
            raise DocumentPermissionDenied()

    async def list_comments(
        self,
        document_id: uuid.UUID,
        proposal_id: uuid.UUID,
        actor_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> CommentListResponse:
        proposal = await self._get_proposal(document_id, proposal_id)
        document = await self._get_document(proposal.document_id)
        await self._ensure_can_view(document, actor_id)

        # total/resolved_count reflect the whole thread, not just this page.
        count_result = await self.session.execute(
            select(
                func.count(CommentORM.id),
                func.count(CommentORM.id).filter(CommentORM.resolved.is_(True)),
            ).where(CommentORM.proposal_id == proposal_id)
        )
        total, resolved_count = count_result.one()

        result = await self.session.execute(
            select(CommentORM)
            .where(CommentORM.proposal_id == proposal_id)
            .order_by(CommentORM.created_at)
            .limit(limit)
            .offset(offset)
        )
        comments = list(result.scalars().all())
        return CommentListResponse(
            comments=[CommentResponse.from_comment(c) for c in comments],
            total=total,
            resolved_count=resolved_count,
        )

    async def create_comment(
        self,
        document_id: uuid.UUID,
        proposal_id: uuid.UUID,
        actor: User,
        payload: CommentCreate,
    ) -> CommentResponse:
        proposal = await self._get_proposal(document_id, proposal_id)
        document = await self._get_document(proposal.document_id)
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot comment on an archived document")
        is_owner = document.owner_id == actor.id
        is_contributor = await self._is_active_contributor(document.id, actor.id)
        if not (is_owner or is_contributor):
            raise DocumentPermissionDenied()

        if payload.parent_id is not None:
            parent = await self._get_comment(payload.parent_id)
            if parent.proposal_id != proposal_id:
                raise CommentNotFound("Parent comment does not belong to this proposal")

        comment = CommentORM(
            proposal_id=proposal_id,
            author_id=actor.id,
            text=payload.text,
            inline=payload.inline,
            line_number=payload.line_number,
            parent_id=payload.parent_id,
            resolved=False,
        )
        comment.author = actor
        self.session.add(comment)
        await self.session.flush()
        await self.session.commit()
        return CommentResponse.from_comment(comment)

    async def update_comment(
        self,
        document_id: uuid.UUID,
        proposal_id: uuid.UUID,
        comment_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: CommentUpdate,
    ) -> CommentResponse:
        await self._get_proposal(document_id, proposal_id)
        comment = await self._get_comment(comment_id)
        if comment.proposal_id != proposal_id:
            raise CommentNotFound()

        document = await self._get_document(document_id)
        is_doc_owner = document.owner_id == actor_id
        is_comment_author = comment.author_id == actor_id

        if payload.text is not None:
            if not is_comment_author:
                raise DocumentPermissionDenied(
                    "Only the comment author can edit its text"
                )
            comment.text = payload.text

        if payload.resolved is not None:
            if not is_doc_owner:
                raise DocumentPermissionDenied(
                    "Only the document owner can (un)resolve comments"
                )
            if payload.resolved:
                comment.resolved = True
                comment.resolved_at = datetime.now(timezone.utc)
                comment.resolved_by = actor_id
            else:
                comment.resolved = False
                comment.resolved_at = None
                comment.resolved_by = None

        await self.session.flush()
        await self.session.commit()
        return CommentResponse.from_comment(comment)

    async def delete_comment(
        self,
        document_id: uuid.UUID,
        proposal_id: uuid.UUID,
        comment_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        await self._get_proposal(document_id, proposal_id)
        comment = await self._get_comment(comment_id)
        if comment.proposal_id != proposal_id:
            raise CommentNotFound()

        document = await self._get_document(document_id)
        is_doc_owner = document.owner_id == actor_id
        is_comment_author = comment.author_id == actor_id
        if not (is_doc_owner or is_comment_author):
            raise DocumentPermissionDenied()

        await self.session.delete(comment)
        await self.session.flush()
        await self.session.commit()
