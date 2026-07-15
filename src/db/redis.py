import redis.asyncio as redis
from src.config import config

JTI_EXPIRY = 3600

token_blocklist = (
    redis.from_url(config.REDIS_URL, decode_responses=True)
    if config.REDIS_URL
    else None
)


def _require_token_blocklist():
    if token_blocklist is None:
        raise RuntimeError("Redis token blocklist is disabled for the MVP.")
    return token_blocklist


async def add_token_to_blocklist(jti: str, expiry: int | None = None) -> None:
    ttl = expiry if expiry and expiry > 0 else JTI_EXPIRY
    await _require_token_blocklist().set(name=jti, value="", ex=ttl)


async def token_in_blocklist(jti: str) -> bool:
    result = await _require_token_blocklist().get(jti)
    return result is not None
