from redis import Redis
from app.core.config import settings

import json

r = settings.redis_url

redis_client = Redis.from_url(
    r,
    decode_responses = True
)

def get_cache_key(short_code: str):
    return f"short:{short_code}"

def get_cache_value(short_code: str) -> dict | None:
    key = get_cache_key(short_code)
    cached_value =  redis_client.get(key)

    if not cached_value:
        return None

    return json.loads(cached_value)

def set_cache_value(short_code: str, long_url: str,url_id: int,  ttl_seconds: int):
    key = get_cache_key(short_code)
    redis_client.setex(key, ttl_seconds, json.dumps({"id": url_id, "long_url": long_url}))

def delete_cached_url(short_code):
    key = get_cache_key(short_code)
    redis_client.delete(key)


    

