from redis.asyncio import Redis
from app.core.config import settings
import json

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

def get_cache_key(short_code: str):
    return f"short:{short_code}"

async def get_cache_value(short_code: str) -> dict | None:
    key = get_cache_key(short_code)
    cached_value = await redis_client.get(key)

    if not cached_value:
        return None

    try:
        return json.loads(cached_value)
    except (TypeError, json.JSONDecodeError):
        await redis_client.delete(key)
        return None

async def set_cache_value(short_code: str, long_url: str, url_id: int, ttl_seconds: int):
    if ttl_seconds <= 0:
        return
    key = get_cache_key(short_code)
    await redis_client.setex(key, ttl_seconds, json.dumps({"id": url_id, "long_url": long_url}))

async def delete_cached_url(short_code: str):
    key = get_cache_key(short_code)
    await redis_client.delete(key)


async def close_redis() -> None:
    await redis_client.aclose()
