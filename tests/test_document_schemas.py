import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.core.documents.schemas import DocumentReadResponse, _build_excerpt
from src.core.documents.service import DocumentService


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


def _fake_version(content, created_at, author_name="Author"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        content=content,
        author_id=uuid.uuid4(),
        author=SimpleNamespace(username=author_name),
        created_at=created_at,
        label="v1",
        message=None,
    )


def test_to_read_response_computes_version_diff_stats():
    now = datetime.now(timezone.utc)
    v1 = _fake_version("hello", now - timedelta(minutes=10))
    v2 = _fake_version("hello world", now)
    fake_document = SimpleNamespace(
        id=uuid.uuid4(),
        title="Test doc",
        state="active",
        owner_id=uuid.uuid4(),
        visibility="private",
        created_at=now,
        updated_at=now,
        published_version_id=v1.id,
        draft_version_id=v2.id,
        versions=[v2, v1],  # deliberately out of order
        contributions=[],
    )

    service = DocumentService(session=None)
    response = service.to_read_response(fake_document)

    assert [v.id for v in response.versions] == [v1.id, v2.id]
    assert response.versions[0].published is True
    assert response.versions[1].published is False
    assert response.versions[1].additions > 0


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


def test_build_excerpt_strips_inline_markdown():
    content = (
        "# Title\n"
        "Freud would have answers. **His answers were too neat.** "
        "I prefer *the rougher version* with `code` and a [link](http://x.com)."
    )

    excerpt = _build_excerpt(content)

    assert "**" not in excerpt
    assert "*" not in excerpt
    assert "`" not in excerpt
    assert "[" not in excerpt and "](" not in excerpt
    assert "His answers were too neat." in excerpt
    assert "the rougher version" in excerpt
    assert "code" in excerpt
    assert "link" in excerpt


def test_build_excerpt_strips_bullets_and_blockquotes():
    content = "- first point\n- second point\n\n> a quote worth keeping"

    excerpt = _build_excerpt(content)

    assert "-" not in excerpt
    assert ">" not in excerpt
    assert "first point" in excerpt
    assert "second point" in excerpt
    assert "a quote worth keeping" in excerpt


def test_build_excerpt_truncates_long_content():
    content = "word " * 100

    excerpt = _build_excerpt(content, limit=50)

    assert len(excerpt) <= 51
    assert excerpt.endswith("…")
