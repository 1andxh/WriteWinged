import uuid
from types import SimpleNamespace

import pytest

from src.core.documents.models import DocumentState, DocumentVisibility
from src.core.versions.service import VersionService
from src.exceptions import DocumentNotFound


class DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class DummySession:
    async def execute(self, statement):
        return DummyResult(None)


class QueueSession:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, statement):
        return DummyResult(self._results.pop(0))


def make_document(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        deleted_at=None,
        state=DocumentState.ACTIVE,
        visibility=DocumentVisibility.PRIVATE,
        published_version_id=None,
        draft_version_id=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_version(document_id: uuid.UUID, **overrides) -> SimpleNamespace:
    defaults = dict(id=uuid.uuid4(), document_id=document_id)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_create_version_raises_document_not_found():
    service = VersionService(session=DummySession())

    with pytest.raises(DocumentNotFound):
        await service.create_version(
            author_id="00000000-0000-0000-0000-000000000001",
            document_id="00000000-0000-0000-0000-000000000002",
            content="test",
        )


@pytest.mark.asyncio
async def test_publish_version_makes_document_public():
    actor_id = uuid.uuid4()
    document = make_document(owner_id=actor_id)
    version = make_version(document.id)
    service = VersionService(session=QueueSession([document, version]))

    await service.publish_version(
        document_id=document.id, version_id=version.id, actor_id=actor_id
    )

    assert document.visibility == DocumentVisibility.PUBLIC
    assert document.published_version_id == version.id


@pytest.mark.asyncio
async def test_unpublish_version_makes_document_private_again():
    actor_id = uuid.uuid4()
    version_id = uuid.uuid4()
    document = make_document(
        owner_id=actor_id,
        visibility=DocumentVisibility.PUBLIC,
        published_version_id=version_id,
    )
    service = VersionService(session=QueueSession([document]))

    await service.unpublish_version(document_id=document.id, actor_id=actor_id)

    assert document.visibility == DocumentVisibility.PRIVATE
    assert document.published_version_id is None
