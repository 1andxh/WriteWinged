import pytest

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


@pytest.mark.asyncio
async def test_create_version_raises_document_not_found():
    service = VersionService(session=DummySession())

    with pytest.raises(DocumentNotFound):
        await service.create_version(
            author_id="00000000-0000-0000-0000-000000000001",
            document_id="00000000-0000-0000-0000-000000000002",
            content="test",
        )
