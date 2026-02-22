import redis.asyncio as redis
from src.config import config

JTI_EXPIRY = 3600

# token_blocklist = aioredis.StrictRedis(
#     url=config.REDIS_URL
# )
token_blocklist = redis.from_url(config.REDIS_URL, decode_responses=True)


async def add_token_to_blocklist(jti: str, expiry: int | None = None) -> None:
    ttl = expiry if expiry and expiry > 0 else JTI_EXPIRY
    await token_blocklist.set(name=jti, value="", ex=ttl)


async def token_in_blocklist(jti: str) -> bool:
    result = await token_blocklist.get(jti)
    return result is not None
