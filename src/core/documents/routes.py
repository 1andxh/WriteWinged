from fastapi import APIRouter, Depends
from ...db.dependency import session
from .schemas import (
    DocumentCommandResponse,
    DocumentCreateRequest,
    DocumentReadResponse,
    DocumentRenameRequest,
)
from .service import DocumentService

# from sqlalchemy.orm import session

document_router = APIRouter()
# document_service = DocumentService()


@document_router.get("", response_model=list[DocumentReadResponse])
def get_public_documents(session: session):
    # documents = awai
    pass
