import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src import app
from src.auth.dependencies import get_current_user
from src.core.comments.dependency import get_comment_service
from src.core.comments.schemas import CommentListResponse, CommentResponse


def fake_user():
    return SimpleNamespace(id=uuid.uuid4(), username="writer")


def make_comment_response(**overrides) -> CommentResponse:
    now = datetime.now(timezone.utc)
    fields = dict(
        id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        author_name="writer",
        author_initials="WR",
        author_color="#2a6b5c",
        text="Looks good",
        created_at=now,
        updated_at=now,
        resolved=False,
        resolved_at=None,
        resolved_by=None,
        inline=False,
        line_number=None,
        parent_id=None,
    )
    fields.update(overrides)
    return CommentResponse(**fields)


def test_list_comments_route_returns_wrapper_shape():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    comment = make_comment_response(proposal_id=proposal_id)

    class FakeCommentService:
        async def list_comments(
            self, document_id, proposal_id, actor_id, limit, offset
        ):
            assert limit == 20
            assert offset == 0
            return CommentListResponse(comments=[comment], total=1, resolved_count=0)

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_comment_service] = lambda: FakeCommentService()
    client = TestClient(app)

    response = client.get(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["resolved_count"] == 0
    assert body["comments"][0]["text"] == "Looks good"


def test_list_comments_route_passes_through_pagination_params():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    seen = {}

    class FakeCommentService:
        async def list_comments(
            self, document_id, proposal_id, actor_id, limit, offset
        ):
            seen["limit"] = limit
            seen["offset"] = offset
            return CommentListResponse(comments=[], total=0, resolved_count=0)

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_comment_service] = lambda: FakeCommentService()
    client = TestClient(app)

    response = client.get(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments",
        params={"limit": 5, "offset": 10},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert seen == {"limit": 5, "offset": 10}


def test_create_comment_route_returns_created_comment():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()

    class FakeCommentService:
        async def create_comment(self, document_id, proposal_id, actor, payload):
            assert payload.text == "Can we soften this?"
            return make_comment_response(proposal_id=proposal_id, text=payload.text)

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_comment_service] = lambda: FakeCommentService()
    client = TestClient(app)

    response = client.post(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments",
        json={"text": "Can we soften this?"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["text"] == "Can we soften this?"


def test_create_comment_route_rejects_inline_without_line_number():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()

    app.dependency_overrides[get_current_user] = fake_user
    client = TestClient(app)

    response = client.post(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments",
        json={"text": "inline note", "inline": True},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_update_comment_route_marks_resolved():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    comment_id = uuid.uuid4()

    class FakeCommentService:
        async def update_comment(
            self, document_id, proposal_id, comment_id, actor_id, payload
        ):
            assert payload.resolved is True
            return make_comment_response(
                proposal_id=proposal_id, resolved=True, resolved_by=actor_id
            )

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_comment_service] = lambda: FakeCommentService()
    client = TestClient(app)

    response = client.patch(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments/{comment_id}",
        json={"resolved": True},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["resolved"] is True


def test_delete_comment_route_returns_204():
    document_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    comment_id = uuid.uuid4()
    deleted = []

    class FakeCommentService:
        async def delete_comment(self, document_id, proposal_id, comment_id, actor_id):
            deleted.append(comment_id)

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_comment_service] = lambda: FakeCommentService()
    client = TestClient(app)

    response = client.delete(
        f"/api/documents/{document_id}/proposals/{proposal_id}/comments/{comment_id}"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 204
    assert deleted == [comment_id]
