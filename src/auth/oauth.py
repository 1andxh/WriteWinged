from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from src.config import config

_starlette_config = StarletteConfig(
    environ={
        "GOOGLE_CLIENT_ID": config.GOOGLE_CLIENT_ID or "",
        "GOOGLE_CLIENT_SECRET": config.GOOGLE_CLIENT_SECRET or "",
    }
)

oauth = OAuth(_starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def google_oauth_configured() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)
