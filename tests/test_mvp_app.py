import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src import app
from src.auth.dependencies import get_auth_service, get_current_user, get_token_service
from src.auth.models import UserRole
from src.auth.service import AccessTokens
from src.config import Config
from src.core.documents.dependency import get_document_service
from src.core.documents.models import DocumentState, DocumentVisibility
from src.exceptions import RevokedTokenException


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


def test_signup_accepts_password_and_does_not_return_hash():
    created_user = SimpleNamespace(
        id=uuid.uuid4(),
        username="writer",
        email="writer@example.com",
        role=UserRole.USER,
        is_verified=False,
    )

    class FakeAuthService:
        async def register(self, payload):
            assert payload.password == "secret123"
            assert not hasattr(payload, "password_hash")
            return created_user

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
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


def test_login_returns_access_and_refresh_tokens():
    login_user = SimpleNamespace(
        id=uuid.uuid4(), email="writer@example.com", role=UserRole.USER
    )

    class FakeAuthService:
        async def authenticate(self, email, password):
            assert email == "writer@example.com"
            assert password == "secret123"
            return login_user

    class FakeTokenService:
        async def issue_token_pair(self, user, user_agent=None, ip_address=None):
            assert user is login_user
            return AccessTokens(
                access_token="issued-access-token",
                refresh_token="issued-refresh-token",
            )

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"email": "writer@example.com", "password": "secret123"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] == "issued-access-token"
    assert body["refresh_token"] == "issued-refresh-token"


def test_refresh_route_rotates_token():
    class FakeTokenService:
        async def refresh_tokens(self, raw_refresh_token):
            assert raw_refresh_token == "old-refresh-token"
            return AccessTokens(
                access_token="new-access-token", refresh_token="new-refresh-token"
            )

    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/refresh", json={"refresh_token": "old-refresh-token"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "new-access-token"
    assert body["refresh_token"] == "new-refresh-token"


def test_refresh_route_rejects_reused_token():
    class FakeTokenService:
        async def refresh_tokens(self, raw_refresh_token):
            raise RevokedTokenException()

    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/refresh", json={"refresh_token": "stolen-token"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_logout_route_revokes_token():
    revoked = []

    class FakeTokenService:
        async def logout(self, raw_refresh_token):
            revoked.append(raw_refresh_token)

    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/logout", json={"refresh_token": "some-refresh-token"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 204
    assert revoked == ["some-refresh-token"]


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
            contributions=[],
        )

    class FakeDocumentService:
        def __init__(self):
            self.deleted = False

        async def get_all_documents(
            self, actor_id, search_query=None, limit=10, offset=0
        ):
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
