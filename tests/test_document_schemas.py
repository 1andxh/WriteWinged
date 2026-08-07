import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from src.core.documents.schemas import DocumentReadResponse


def _fake_contribution(user_id, email, username):
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        document_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        revoked_at=None,
        user=SimpleNamespace(id=user_id, email=email, username=username),
    )


def test_document_read_response_serializes_contributions():
    owner_id = uuid.uuid4()
    contributor_id = uuid.uuid4()
    fake_document = SimpleNamespace(
        id=uuid.uuid4(),
        title="Test doc",
        state="active",
        owner_id=owner_id,
        visibility="private",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        published_version_id=None,
        draft_version_id=None,
        versions=[],
        contributions=[
            _fake_contribution(contributor_id, "contributor@example.com", "contributor")
        ],
    )

    response = DocumentReadResponse.model_validate(fake_document)

    assert len(response.contributions) == 1
    assert response.contributions[0].email == "contributor@example.com"
    assert response.contributions[0].name == "contributor"
    assert response.contributions[0].role == "contributor"


def test_document_read_response_with_no_contributions():
    fake_document = SimpleNamespace(
        id=uuid.uuid4(),
        title="Test doc",
        state="active",
        owner_id=uuid.uuid4(),
        visibility="private",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        published_version_id=None,
        draft_version_id=None,
        versions=[],
        contributions=[],
    )

    response = DocumentReadResponse.model_validate(fake_document)

    assert response.contributions == []
