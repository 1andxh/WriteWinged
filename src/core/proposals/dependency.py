from ...db.dependency import session
from .services import ProposalService


async def get_proposal_service(session: session) -> ProposalService:
    return ProposalService(session)
