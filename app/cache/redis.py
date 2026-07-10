from redis import Redis
from app.core.config import settings

r = settings.redis_url

redis_client = Redis.from_url(
    r,
    decode_responses = True
)

def get_cache_key(short_code: str):
    return f"short:{short_code}"

def get_cache_long_url(short_code: str) -> str | None:
    key = get_cache_key(short_code)
    return redis_client.get(key)

def set_cache_long_url(short_code: str, long_url: str, ttl_seconds: int):
    key = get_cache_key(short_code)
    redis_client.setex(key, ttl_seconds, long_url)

def delete_cached_url(short_code):
    key = get_cache_key(short_code)
    redis_client.delete(key)

    

