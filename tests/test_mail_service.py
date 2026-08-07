from types import SimpleNamespace

import pytest
from itsdangerous import URLSafeTimedSerializer

from src.exceptions import InvalidTokenException
from src.mail.service import INVITE_TOKEN_MAX_AGE_SECONDS, MailService
from src.mail.utils import decode_url_safe_token


def make_config(**overrides):
    fields = dict(
        EMAIL_SECRET="email-secret",
        JWT_SECRET="jwt-secret",
        PASSWORD_RESET_SECRET="reset-secret",
        DOMAIN="localhost:8000",
        FRONTEND_URL=None,
        ALLOWED_ORIGINS="http://localhost:5173",
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_decode_url_safe_token_default_max_age_is_unchanged():
    """Regression: adding the optional max_age param must not change the
    default behaviour verify/reset already rely on."""
    serializer = URLSafeTimedSerializer("secret", salt="s")
    token = serializer.dumps({"a": 1})

    assert decode_url_safe_token(token, serializer) == {"a": 1}


def test_decode_url_safe_token_respects_explicit_max_age():
    serializer = URLSafeTimedSerializer("secret", salt="s")
    token = serializer.dumps({"a": 1})

    # A negative max_age can never be satisfied, regardless of how little
    # time has elapsed since dumps() -- deterministic without mocking time.
    with pytest.raises(InvalidTokenException):
        decode_url_safe_token(token, serializer, max_age=-1)


def test_frontend_base_prefers_frontend_url_over_allowed_origins():
    service = MailService(make_config(FRONTEND_URL="https://app.limarr.com"))
    assert service.frontend_base == "https://app.limarr.com"


def test_frontend_base_falls_back_to_allowed_origins():
    service = MailService(make_config(FRONTEND_URL=None))
    assert service.frontend_base == "http://localhost:5173"


def test_invite_token_round_trip():
    service = MailService(make_config())
    token = service.create_invite_token(
        {
            "email": "invitee@example.com",
            "document_id": "11111111-1111-1111-1111-111111111111",
            "type": "contributor-invite",
        }
    )

    data = service.decode_invite_token(token)

    assert data["email"] == "invitee@example.com"
    assert data["document_id"] == "11111111-1111-1111-1111-111111111111"


def test_invite_token_rejects_wrong_type():
    service = MailService(make_config())
    # Reuse the password-reset serializer's salt space by crafting a token
    # with the invite serializer but the wrong "type" field.
    token = service.invite_serializer.dumps(
        {"email": "invitee@example.com", "document_id": "x", "type": "password-reset"}
    )

    with pytest.raises(InvalidTokenException):
        service.decode_invite_token(token)


def test_invite_token_rejects_token_from_a_different_serializer():
    service = MailService(make_config())
    # A verification token, signed with a different salt, must not be
    # accepted by the invite decoder even though both use the same secret.
    foreign_token = service.email_serializer.dumps(
        {
            "email": "invitee@example.com",
            "document_id": "x",
            "type": "contributor-invite",
        }
    )

    with pytest.raises(InvalidTokenException):
        service.decode_invite_token(foreign_token)


def test_invite_token_max_age_is_seven_days():
    assert INVITE_TOKEN_MAX_AGE_SECONDS == 60 * 60 * 24 * 7
