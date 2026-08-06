import uuid
from types import SimpleNamespace

from authlib.integrations.starlette_client import OAuthError
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from src import app
from src.auth import routes as auth_routes
from src.auth.dependencies import get_auth_service, get_token_service
from src.auth.service import AccessTokens


class FakeGoogleClient:
    def __init__(self, *, redirect_result=None, token_result=None, raise_error=None):
        self.redirect_result = redirect_result
        self.token_result = token_result
        self.raise_error = raise_error

    async def authorize_redirect(self, request, redirect_uri):
        return self.redirect_result

    async def authorize_access_token(self, request):
        if self.raise_error:
            raise self.raise_error
        return self.token_result


def test_google_login_route_returns_503_when_not_configured(monkeypatch):
    monkeypatch.setattr(auth_routes, "google_oauth_configured", lambda: False)
    client = TestClient(app)

    response = client.get("/api/auth/google", follow_redirects=False)

    assert response.status_code == 503


def test_google_login_route_redirects_when_configured(monkeypatch):
    fake_client = FakeGoogleClient(
        redirect_result=RedirectResponse("https://accounts.google.com/o/oauth2/auth")
    )
    monkeypatch.setattr(auth_routes, "google_oauth_configured", lambda: True)
    monkeypatch.setattr(auth_routes.oauth, "google", fake_client)
    client = TestClient(app)

    response = client.get("/api/auth/google", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "https://accounts.google.com/o/oauth2/auth"


def test_google_callback_route_issues_tokens_on_success(monkeypatch):
    user = SimpleNamespace(
        id=uuid.uuid4(), email="writer@example.com", username="writer"
    )

    class FakeAuthService:
        async def authenticate_via_google(self, google_user):
            assert google_user.sub == "sub-1"
            assert google_user.email == "writer@example.com"
            return user

    class FakeTokenService:
        async def issue_token_pair(self, actor, user_agent=None, ip_address=None):
            assert actor is user
            return AccessTokens(access_token="access-tok", refresh_token="refresh-tok")

    fake_client = FakeGoogleClient(
        token_result={
            "userinfo": {
                "sub": "sub-1",
                "email": "writer@example.com",
                "name": "Writer",
            }
        }
    )
    monkeypatch.setattr(auth_routes.oauth, "google", fake_client)
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    client = TestClient(app)

    response = client.get("/api/auth/callback/google")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "access-tok"
    assert body["refresh_token"] == "refresh-tok"


def test_google_callback_route_rejects_oauth_error(monkeypatch):
    fake_client = FakeGoogleClient(raise_error=OAuthError("mismatching_state"))
    monkeypatch.setattr(auth_routes.oauth, "google", fake_client)
    client = TestClient(app)

    response = client.get("/api/auth/callback/google")

    assert response.status_code == 401


def test_google_callback_route_rejects_missing_userinfo(monkeypatch):
    fake_client = FakeGoogleClient(token_result={})
    monkeypatch.setattr(auth_routes.oauth, "google", fake_client)
    client = TestClient(app)

    response = client.get("/api/auth/callback/google")

    assert response.status_code == 401
