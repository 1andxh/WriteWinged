from pydantic_settings import SettingsConfigDict, BaseSettings
from pydantic import SecretStr


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class Config(CustomBaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    API_VERSION: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    MIDDLEWARE_SECRET: str
    REDIS_URL: str

    # mail config
    MAIL_USERNAME: str
    MAIL_PASSWORD: SecretStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    DOMAIN: str
    EMAIL_SECRET: str
    PASSWORD_RESET_SECRET: str


config = Config()  # type: ignore
