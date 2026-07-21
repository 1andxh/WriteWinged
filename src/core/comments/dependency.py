from ...db.dependency import session
from .service import CommentService


async def get_comment_service(session: session) -> CommentService:
    return CommentService(session)
