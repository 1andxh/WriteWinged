import uuid

from src.core.documents import DocumentORM
from src.core.documents.models import DocumentState
from src.core.versions.diff import compute_diff
from src.core.versions.models import VersionORM
from src.core.versions.schemas import VersionRead
from src.exceptions import (
    DocumentNotMutable,
    VersionMismatch,
)


def can_author_version(document: DocumentORM):
    # if document is None:
    #     raise DocumentNotFound()
    if document.deleted_at is not None or document.state != DocumentState.ACTIVE:
        raise DocumentNotMutable("Document state does not permit creation")


def can_publish_version(document: DocumentORM):
    if document.deleted_at is not None or document.state == DocumentState.ARCHIVED:
        raise DocumentNotMutable("Document is archived or deleted")


def ensure_version_belongs(version: VersionORM, document_id: uuid.UUID):
    if version.document_id != document_id:
        raise VersionMismatch()


def build_version_reads(
    versions: list[VersionORM], published_version_id: uuid.UUID | None
) -> list[VersionRead]:
    sorted_versions = sorted(versions, key=lambda v: v.created_at)
    reads: list[VersionRead] = []
    previous_content = ""
    for version in sorted_versions:
        _, additions, deletions = compute_diff(previous_content, version.content)
        reads.append(
            VersionRead.from_version(
                version,
                published=version.id == published_version_id,
                additions=additions,
                deletions=deletions,
            )
        )
        previous_content = version.content
    return reads


# i could still use a class property for this.
