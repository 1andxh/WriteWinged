import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select

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
    UserNotFoundException,
)

from .models import ContributionORM
from .schemas import ListContributor

# nts: borrowing another class? just add to __init__ and create an instance


class ContributionService:
    def __init__(self, session: session) -> None:
        self.session = session
        self.doc_service = DocumentService(session)
        self.user_service = UserService(session)

    def _is_owner(self, actor_id: uuid.UUID, document: DocumentORM) -> bool:
        return document.owner_id == actor_id

    async def add_contributor(
        self, *, document_id: uuid.UUID, email: str, actor_id: uuid.UUID
    ) -> ListContributor:
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

        contribution = ContributionORM(
            document_id=document.id,
            user_id=target_user.id,
            created_at=datetime.now(timezone.utc),
        )
        contribution.user = target_user
        self.session.add(contribution)
        await self.session.flush()
        await self.session.commit()
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
        await self.session.commit()

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

    # async def accept_contribution(self):
    #     pass

    # async def request_to_contribute(self):
    #     pass
