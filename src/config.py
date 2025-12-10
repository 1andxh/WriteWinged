from pydantic_settings import SettingsConfigDict, BaseSettings


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


config = Config()  # type: ignore
