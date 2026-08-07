from typing import Annotated

from fastapi import Depends

from ...db.dependency import session
from ...mail.dependency import get_mail_service
from ...mail.service import MailService
from .services import ProposalService


async def get_proposal_service(
    session: session,
    mail_service: Annotated[MailService, Depends(get_mail_service)],
) -> ProposalService:
    return ProposalService(session, mail_service)
