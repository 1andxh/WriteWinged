import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src import app
from src.auth.dependencies import get_mail_service, get_user_service
from src.exceptions import InvalidTokenException, UserNotFoundException


def make_user(**overrides):
    fields = dict(
        id=uuid.uuid4(),
        email="writer@example.com",
        username="writer",
        is_verified=False,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_verify_route_marks_user_verified():
    user = make_user(is_verified=False)
    updated = {}

    class FakeUserService:
        async def get_user_by_email(self, email):
            assert email == "writer@example.com"
            return user

        async def update_user(self, user, fields):
            updated.update(fields)
            return user

    class FakeMailService:
        def decode_email_verification_token(self, token):
            assert token == "good-token"
            return "writer@example.com"

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.get("/api/auth/verify", params={"token": "good-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert updated == {"is_verified": True}
    assert response.json()["message"] == "Account verified successfully"


def test_verify_route_is_idempotent_for_already_verified_user():
    user = make_user(is_verified=True)

    class FakeUserService:
        async def get_user_by_email(self, email):
            return user

        async def update_user(self, user, fields):
            raise AssertionError("should not update an already-verified user")

    class FakeMailService:
        def decode_email_verification_token(self, token):
            return "writer@example.com"

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.get("/api/auth/verify", params={"token": "good-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["message"] == "Account already verified"


def test_verify_route_rejects_invalid_token():
    class FakeMailService:
        def decode_email_verification_token(self, token):
            raise InvalidTokenException()

    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.get("/api/auth/verify", params={"token": "bad-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_verify_route_rejects_unknown_user():
    class FakeUserService:
        async def get_user_by_email(self, email):
            return None

    class FakeMailService:
        def decode_email_verification_token(self, token):
            return "ghost@example.com"

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.get("/api/auth/verify", params={"token": "good-token"})

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"] == UserNotFoundException().__class__.__name__


def test_request_password_reset_sends_for_known_email():
    user = make_user()
    sent_to = []

    class FakeUserService:
        async def get_user_by_email(self, email):
            return user

    class FakeMailService:
        async def send_password_reset_email(self, email):
            sent_to.append(email)

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/request-password-reset", json={"email": "writer@example.com"}
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert sent_to == ["writer@example.com"]


def test_request_password_reset_does_not_reveal_unknown_email():
    class FakeUserService:
        async def get_user_by_email(self, email):
            return None

    class FakeMailService:
        async def send_password_reset_email(self, email):
            raise AssertionError("should not send for an unknown email")

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    known = client.post(
        "/api/auth/request-password-reset", json={"email": "ghost@example.com"}
    )

    app.dependency_overrides.clear()

    assert known.status_code == 200
    assert known.json()["message"] == "If that email exists, a reset link has been sent"


def test_reset_password_route_updates_password():
    user = make_user()
    new_passwords = []

    class FakeUserService:
        async def get_user_by_email(self, email):
            assert email == "writer@example.com"
            return user

        async def set_password(self, user, new_password):
            new_passwords.append(new_password)
            return user

    class FakeMailService:
        def decode_password_reset_token(self, token):
            assert token == "good-token"
            return "writer@example.com"

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/reset-password",
        params={"token": "good-token"},
        json={"new_password": "new-secret-1", "confirm_new_password": "new-secret-1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert new_passwords == ["new-secret-1"]


def test_reset_password_route_rejects_mismatched_passwords():
    client = TestClient(app)

    response = client.post(
        "/api/auth/reset-password",
        params={"token": "good-token"},
        json={"new_password": "new-secret-1", "confirm_new_password": "different"},
    )

    assert response.status_code == 422


def test_reset_password_route_rejects_unknown_user():
    class FakeUserService:
        async def get_user_by_email(self, email):
            return None

    class FakeMailService:
        def decode_password_reset_token(self, token):
            return "ghost@example.com"

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    app.dependency_overrides[get_mail_service] = lambda: FakeMailService()
    client = TestClient(app)

    response = client.post(
        "/api/auth/reset-password",
        params={"token": "good-token"},
        json={"new_password": "new-secret-1", "confirm_new_password": "new-secret-1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 404
