from pydantic_settings import BaseSettings, SettingsConfigDict


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class Config(CustomBaseSettings):
    DATABASE_URL: str
    SQL_ECHO: bool = False
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    API_VERSION: str = "0.1.0"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"
    LOG_REQUESTS: bool = True

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    MIDDLEWARE_SECRET: str | None = None
    REDIS_URL: str | None = None
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    DOMAIN: str | None = None
    EMAIL_SECRET: str | None = None
    PASSWORD_RESET_SECRET: str | None = None
    # Base URL for links embedded in transactional emails (invites, proposal
    # notifications) that must point at the SvelteKit frontend, not this API.
    FRONTEND_URL: str | None = None


config = Config()  # type: ignore
