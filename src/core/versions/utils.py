from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState
from src.exceptions import DocumentNotFound, DocumentNotMutable


def can_author_version(document: DocumentORM):
    if not document:
        raise DocumentNotFound()
    if document.deleted_at is not None or document.state != DocumentState.ACTIVE:
        raise DocumentNotMutable("Document state does not permit creation")


def can_publish_version(document: DocumentORM):
    if not document:
        raise DocumentNotFound()
    if document.deleted_at is not None or document.state == DocumentState.ARCHIVED:
        raise DocumentNotMutable("Document is archived or deleted")
