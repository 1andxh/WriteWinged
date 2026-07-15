from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient

from src import app
from src.auth.models import UserRole
from src.auth import routes as auth_routes
from src.auth.utils import hash_password
from src.config import Config
from src.core.documents.dependency import get_document_service
from src.core.documents.models import DocumentState, DocumentVisibility
from src.db.main import get_session
from src.auth.dependencies import get_current_user


async def fake_session():
    yield object()


def test_app_imports_with_minimal_mvp_config():
    cfg = Config(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@db:5432/writewinged",
        JWT_SECRET="secret",
    )

    assert cfg.REDIS_URL is None
    assert cfg.MAIL_USERNAME is None
    assert cfg.GOOGLE_CLIENT_ID is None
    assert cfg.JWT_ALGORITHM == "HS256"
    assert cfg.ALLOWED_HOSTS == "localhost,127.0.0.1,testserver"


def test_compose_uses_only_api_db_and_env_based_healthcheck():
    compose = open("docker-compose.yaml", encoding="utf-8").read()

    assert "writewinged_redis" not in compose
    assert "redis:" not in compose
    assert "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}" in compose


def test_health_route_responds():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_document_static_routes_are_before_uuid_route():
    document_paths = [
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/documents")
    ]

    archive_index = document_paths.index("/api/documents/archive")
    detail_index = document_paths.index("/api/documents/{document_id}")

    assert archive_index < detail_index


def test_signup_accepts_password_and_does_not_return_hash(monkeypatch):
    created_user = SimpleNamespace(
        id=uuid.uuid4(),
        username="writer",
        email="writer@example.com",
        role=UserRole.USER,
        is_verified=False,
    )

    class FakeUserService:
        async def check_user_exists(self, email, session):
            return False

        async def create_user(self, payload, session):
            assert payload.password == "secret123"
            assert not hasattr(payload, "password_hash")
            return created_user

    monkeypatch.setattr(auth_routes, "user_service", FakeUserService())
    app.dependency_overrides[get_session] = fake_session
    client = TestClient(app)

    response = client.post(
        "/api/auth/signup",
        json={
            "username": "writer",
            "email": "writer@example.com",
            "password": "secret123",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "writer@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_login_returns_single_bearer_token(monkeypatch):
    login_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="writer@example.com",
        role=UserRole.USER,
        password_hash=hash_password("secret123"),
    )

    class FakeUserService:
        async def get_user_by_email(self, email, session):
            return login_user

    monkeypatch.setattr(auth_routes, "user_service", FakeUserService())
    app.dependency_overrides[get_session] = fake_session
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"email": "writer@example.com", "password": "secret123"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "refresh_token" not in body


def test_document_routes_call_service_with_frontend_friendly_shapes():
    user_id = uuid.uuid4()
    document_id = uuid.uuid4()

    def make_document(title="Draft"):
        return SimpleNamespace(
            id=document_id,
            title=title,
            state=DocumentState.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            owner_id=user_id,
            created_at="2026-06-02T00:00:00Z",
            updated_at="2026-06-02T00:00:00Z",
            versions=[],
            contributors=[],
        )

    class FakeDocumentService:
        def __init__(self):
            self.deleted = False

        async def get_all_documents(self, actor_id, search_query=None, limit=10, offset=0):
            assert actor_id == user_id
            return [make_document()]

        async def get_archived_documents(
            self, actor_id, search_query=None, limit=10, offset=0
        ):
            assert actor_id == user_id
            return [make_document()]

        async def get_document(self, document_id):
            return make_document()

        async def create_document(self, actor_id, title):
            assert actor_id == user_id
            return make_document(title=title)

        async def rename_document(self, actor_id, document_id, title):
            assert actor_id == user_id
            return make_document(title=title)

        async def archive_document(self, document_id, actor_id):
            assert actor_id == user_id
            return make_document()

        async def delete_document(self, document_id, actor_id):
            assert actor_id == user_id
            self.deleted = True

    fake_service = FakeDocumentService()

    async def fake_current_user():
        return SimpleNamespace(id=user_id)

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_document_service] = lambda: fake_service
    client = TestClient(app)

    assert client.get("/api/documents/me").status_code == 200
    assert client.get("/api/documents/archive").status_code == 200
    assert client.get(f"/api/documents/{document_id}").status_code == 200

    create_response = client.post("/api/documents/", json={"title": "New draft"})
    rename_response = client.patch(
        f"/api/documents/{document_id}/rename", json={"title": "Renamed"}
    )
    archive_response = client.post(f"/api/documents/{document_id}/archive")
    delete_response = client.delete(f"/api/documents/{document_id}/")

    app.dependency_overrides.clear()

    assert create_response.json()["title"] == "New draft"
    assert rename_response.json()["id"] == str(document_id)
    assert archive_response.json()["id"] == str(document_id)
    assert delete_response.status_code == 204
    assert fake_service.deleted is True
