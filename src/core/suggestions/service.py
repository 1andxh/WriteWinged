from fastapi.exceptions import HTTPException
from fastapi import status
from ...db.dependency import session
from ...auth.models import User
from .models import Suggestion, SuggestionStatus
from ..versions.models import Version
import uuid
from ...exceptions import DocumentNotAcceptingSuggestionsError, ResourceNotFoundError
from datetime import datetime as dt, timezone
from sqlalchemy import select, s

now = dt.now(timezone.utc)


class SuggestionService:
    def create_suggestion(self, suggestion_data: dict, session: session):
        pass

    async def submit_suggestion(
        self,
        *,
        session: session,
        base_version_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str
    ) -> Suggestion:
        base_version = await session.get(Version, base_version_id)  # type: ignore
        if base_version is None:
            raise ResourceNotFoundError("Base version not found")

        document = base_version.document
        if document is None:
            raise ResourceNotFoundError("cannot contribute to non existent document")
        statement = select(Collaborator).where(
            Collaborator.document_id == document.id, Collaborator.user_id == author_id
        )
        result = await session.execute(statement)
        collaboration = result.scalar_one_or_none()

        if document.is_archived or document.is_locked:
            raise DocumentNotAcceptingSuggestionsError()

        if author.role not in ["editor", "collaorator", "admin"]:
            raise NoPermissionError("Not allowed to submit suggestions")

        content = content.strip()
        if not content:
            raise ValueError("Suggestioin content cannot be empty")

        suggestion = Suggestion(
            document_id=document.id,
            base_version_id=base_version.id,
            author_id=author.id,
            content=content,
            status=SuggestionStatus.PENDING,
            created_at=now(),
        )

        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)

        return suggestion

    async def accept_suggestion(self): ...

    # async def reject_submission(self): ...
