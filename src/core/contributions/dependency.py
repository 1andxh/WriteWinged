from typing import Annotated

from fastapi import Depends

from ...db.dependency import session
from ...mail.dependency import get_mail_service
from ...mail.service import MailService
from .services import ContributionService


async def get_contribution_service(
    session: session,
    mail_service: Annotated[MailService, Depends(get_mail_service)],
) -> ContributionService:
    return ContributionService(session, mail_service)
