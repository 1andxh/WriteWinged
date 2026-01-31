from ...db.dependency import session
from .service import VersionService


async def get_version_service(session: session) -> VersionService:
    return VersionService(session)
