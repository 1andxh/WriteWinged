import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError

from src.auth import User
from src.auth.service import UserService
from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState
from src.core.documents.service import DocumentService
from src.db.dependency import session
from src.exceptions import (
    ContributionAlreadyExists,
    ContributionAlreadyRevoked,
    ContributionNotFound,
    DocumentNotFound,
    DocumentPermissionDenied,
    InvalidContributionTarget,
    InvalidDocumentState,
    InvitationEmailMismatch,
    UserNotFoundException,
)
from src.mail.service import MailService

from .models import ContributionORM
from .schemas import InvitePreviewResponse, InviteSentResponse, ListContributor

# nts: borrowing another class? just add to __init__ and create an instance


class ContributionService:
    def __init__(self, session: session, mail_service: MailService) -> None:
        self.session = session
        self.doc_service = DocumentService(session)
        self.user_service = UserService(session)
        self.mail_service = mail_service

    def _is_owner(self, actor_id: uuid.UUID, document: DocumentORM) -> bool:
        return document.owner_id == actor_id

    async def invite_contributor(
        self,
        *,
        document_id: uuid.UUID,
        email: str,
        actor_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> InviteSentResponse:
        target_user = await self.user_service.get_user_by_email(email)
        if target_user is None:
            raise UserNotFoundException()

        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()

        if not self._is_owner(actor_id=actor_id, document=document):
            raise DocumentPermissionDenied()
        if target_user.id == document.owner_id:
            raise InvalidContributionTarget()

        statement = select(ContributionORM).where(
            ContributionORM.document_id == document_id,
            ContributionORM.user_id == target_user.id,
        )
        result = await self.session.execute(statement)
        existing_contribution = result.scalar_one_or_none()
        if existing_contribution is not None:
            raise ContributionAlreadyExists()

        inviter = await self.user_service.get_user_by_id(actor_id)
        background_tasks.add_task(
            self.mail_service.send_contributor_invite_email,
            invitee_email=target_user.email,
            inviter_name=inviter.username if inviter else "A Limarr user",
            document_id=document.id,
            document_title=document.title,
        )
        return InviteSentResponse(message="Invitation sent", email=target_user.email)

    async def _decode_invitation(
        self, *, token: str, actor: User
    ) -> tuple[dict, uuid.UUID]:
        data = self.mail_service.decode_invite_token(token)
        if actor.email.lower() != data["email"].lower():
            raise InvitationEmailMismatch()
        return data, uuid.UUID(data["document_id"])

    async def preview_invitation(
        self, *, token: str, actor: User
    ) -> InvitePreviewResponse:
        data, document_id = await self._decode_invitation(token=token, actor=actor)

        statement = select(DocumentORM).where(
            DocumentORM.id == document_id, DocumentORM.deleted_at.is_(None)
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()

        owner = await self.user_service.get_user_by_id(document.owner_id)
        return InvitePreviewResponse(
            document_id=document.id,
            document_title=document.title,
            inviter_name=owner.username if owner else "A Limarr user",
            invitee_email=data["email"],
        )

    async def accept_invitation(self, *, token: str, actor: User) -> ListContributor:
        _, document_id = await self._decode_invitation(token=token, actor=actor)

        # Re-fetch and revalidate the document at accept time (not just at
        # invite time) -- ownership or document state may have changed in
        # the days between the invite being sent and being accepted.
        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None or document.deleted_at is not None:
            raise DocumentNotFound()
        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot join an archived document")
        if actor.id == document.owner_id:
            raise InvalidContributionTarget()

        statement = select(ContributionORM).where(
            ContributionORM.document_id == document.id,
            ContributionORM.user_id == actor.id,
        )
        result = await self.session.execute(statement)
        existing_contribution = result.scalar_one_or_none()
        if existing_contribution is not None:
            raise ContributionAlreadyExists()

        contribution = ContributionORM(
            document_id=document.id,
            user_id=actor.id,
            created_at=datetime.now(timezone.utc),
        )
        contribution.user = actor
        self.session.add(contribution)
        try:
            await self.session.flush()
        except IntegrityError:
            # A double-click, two open tabs, or a retried request can race
            # between the pre-check above and this insert; the DB's
            # uq_contribution_document_user constraint is the real guard.
            raise ContributionAlreadyExists() from None
        return ListContributor.from_contribution(contribution)

    async def revoke_contributor(
        self,
        *,
        document_id: uuid.UUID,
        contributor_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:

        statement = (
            select(DocumentORM).where(DocumentORM.id == document_id).with_for_update()
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            raise DocumentNotFound()
        if not self._is_owner(actor_id=actor_id, document=document):
            raise DocumentPermissionDenied()

        statement = select(ContributionORM).where(
            ContributionORM.document_id == document_id,
            ContributionORM.user_id == contributor_id,
        )
        result = await self.session.execute(statement)
        contribution = result.scalar_one_or_none()

        if contribution is None:
            raise ContributionNotFound()

        #  nts: invariants deserve redundancy --just check anyways

        if contribution.revoked_at is not None:
            raise ContributionAlreadyRevoked()

        contribution.revoked_at = datetime.now(timezone.utc)

        await self.session.flush()

    async def list_contributors(
        self,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> list[ListContributor]:
        statement = select(DocumentORM).where(
            DocumentORM.id == document_id, DocumentORM.deleted_at.is_(None)
        )
        result = await self.session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFound()

        if document.state == DocumentState.ARCHIVED:
            raise InvalidDocumentState("Cannot read archived document")

        if not self._is_owner(actor_id=actor_id, document=document):
            statement = select(ContributionORM.id).where(
                ContributionORM.document_id == document_id,
                ContributionORM.user_id == actor_id,
                ContributionORM.revoked_at.is_(None),
            )
            result = await self.session.execute(statement)
            is_contributor = result.scalar_one_or_none()

            if not is_contributor:
                raise DocumentPermissionDenied()

        statement = await self.session.execute(
            select(ContributionORM)
            .where(
                ContributionORM.document_id == document_id,
                ContributionORM.revoked_at.is_(None),
            )
            .order_by(desc(ContributionORM.created_at))
        )
        contributors = statement.scalars().all()

        owner = await self.user_service.get_user_by_id(document.owner_id)
        rows = [ListContributor.from_owner(document, owner)]
        rows += [ListContributor.from_contribution(c) for c in contributors]
        return rows
