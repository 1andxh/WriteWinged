from datetime import datetime, timezone
from urllib.parse import quote

from itsdangerous import URLSafeTimedSerializer

from ..auth.models import User
from ..auth.templates import templates
from ..exceptions import InvalidTokenException
from .mail import create_message, mail
from .utils import decode_url_safe_token


class MailService:
    def __init__(self, config) -> None:
        email_secret = config.EMAIL_SECRET or config.JWT_SECRET
        reset_secret = config.PASSWORD_RESET_SECRET or config.JWT_SECRET
        self.domain = config.DOMAIN or "localhost:8000"
        self.email_serializer = URLSafeTimedSerializer(
            secret_key=email_secret, salt="email-verification"
        )
        self.password_reset_serializer = URLSafeTimedSerializer(
            secret_key=reset_secret, salt="password-reset"
        )

    def create_email_verification_token(self, data: dict) -> str:
        return self.email_serializer.dumps(data)

    def create_password_reset_token(self, data: dict) -> str:
        return self.password_reset_serializer.dumps(data)

    def decode_email_verification_token(self, token: str) -> str:
        data = decode_url_safe_token(token, self.email_serializer)
        email = data.get("email")
        if not email:
            raise InvalidTokenException()
        return email

    def decode_password_reset_token(self, token: str) -> str:
        data = decode_url_safe_token(token, self.password_reset_serializer)
        if data.get("type") != "password-reset" or not data.get("email"):
            raise InvalidTokenException()
        return data["email"]

    async def _send(self, recipients: list[str], subject: str, html: str) -> None:
        message = create_message(recipients=recipients, subject=subject, body=html)
        await mail.send_message(message)

    async def send_verification_email(self, user: User) -> None:
        token = self.create_email_verification_token({"email": user.email})
        link = f"https://{self.domain}/api/auth/verify?token={quote(token, safe='')}"
        html = templates.get_template("verify_email.html").render(
            username=user.username, link=link, year=datetime.now(timezone.utc).year
        )
        await self._send([user.email], "Verify your email address", html)

    async def send_password_reset_email(self, email: str) -> None:
        token = self.create_password_reset_token(
            {"email": email, "type": "password-reset"}
        )
        link = (
            f"https://{self.domain}/api/auth/reset-password?token="
            f"{quote(token, safe='')}"
        )
        html = templates.get_template("password_reset.html").render(
            link=link, year=datetime.now(timezone.utc).year
        )
        await self._send([email], "Reset your password", html)
