from ...db.dependency import session
from ...auth.models import User
from .models import Suggestion
import uuid


class SuggestionService:
    async def submit_suggestion(
        self, *, session: session, document_id: uuid.UUID, author: User, content: str
    ):
        # document = await session.get(document_id)

        # return Suggestion
        pass

    async def accept_submission(self): ...

    async def reject_submission(self): ...
