from ...db.dependency import session
from .service import DocumentService


async def get_document_service(session: session) -> DocumentService:
    return DocumentService(session)
