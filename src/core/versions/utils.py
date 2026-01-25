from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState
from src.exceptions import (
    DocumentNotFound,
    DocumentNotMutable,
    VersionDoesNotExist,
    VersionMismatch,
)
from src.core.versions.models import VersionORM
import uuid


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


def ensure_version_belongs(version: VersionORM | None, document_id: uuid.UUID):
    if version is None:
        raise VersionDoesNotExist()
    if version.document_id != document_id:
        raise VersionMismatch()


# i could still use a class property for this.
