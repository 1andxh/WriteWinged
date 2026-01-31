from ...db.dependency import session
from .services import ContributionService


async def get_document_service(session: session) -> ContributionService:
    return ContributionService(session)
