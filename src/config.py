from pydantic_settings import SettingsConfigDict, BaseSettings


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class Config(CustomBaseSettings):
    DATABASE_URL: str
    SQL_ECHO: bool = False
    ENVIRONMENT: str = "development"
    DB_STARTUP_MAX_WAIT_SECONDS: int = 30
    DB_STARTUP_RETRY_INTERVAL_SECONDS: int = 2
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    API_VERSION: str = "0.1.0"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"
    LOG_REQUESTS: bool = True

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    REDIS_URL: str | None = None
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_PORT: int | None = None
    MAIL_SERVER: str | None = None
    MAIL_FROM: str | None = None
    MAIL_FROM_NAME: str | None = None
    DOMAIN: str | None = None
    EMAIL_SECRET: str | None = None
    PASSWORD_RESET_SECRET: str | None = None


config = Config()  # type: ignore
