from itsdangerous import URLSafeTimedSerializer
from src.config import config


class MailService:
    def __init__(self, config) -> None:
        self.email_serializer = URLSafeTimedSerializer(
            secret_key=config.EMAIL_SECRET, salt="email-verification"
        )

        self.password_reset_serializer = URLSafeTimedSerializer(
            secret_key=config.PASSWORD_RESET_SECRET, salt="password-reset"
        )

    def email_verification_token(self, data: dict):
        return self.email_serializer.dumps(data)

    def password_reset_token(self, data: dict):
        return self.password_reset_serializer.dumps(data)
