from fastapi.exceptions import HTTPException
from fastapi import status
from ...db.dependency import session
from ...auth.models import User
from .models import Suggestion
from ..versions.models import Version
import uuid
from ...exceptions import DocumentNotAcceptingSuggestionsError


class SuggestionService:
    async def submit_suggestion(
        self, *, session: session, base_version: uuid.UUID, author: User, content: str
    ):
        base_version = await session.get(Version, base_version_id)  # type: ignore
        if base_version is None:
            raise NotFoundError("Base version not found")

        document = base_version.document

        #         # return Suggestion
        #         pass

        if document.is_archived or document.is_locked:
            raise DocumentNotAcceptingSuggestionsError()

    # async def accept_submission(self): ...

    # async def reject_submission(self): ...
