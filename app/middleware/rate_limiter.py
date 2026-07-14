from fastapi import Request,status, Response
from datetime import datetime, UTC
import math 
from app.cache.redis import redis_client

from pathlib import Path

BUCKET_CAPACITY_AUTH = 5
TOKEN_FILL_RATE_AUTH = 0.1

BUCKET_CAPACITY_API = 30
TOKEN_FILL_RATE_API = 1

BUCKET_CAPACITY_REDIRECT = 100
TOKEN_FILL_RATE_REDIRECT = 10   

LUA_SCRIPT_PATH = Path(__file__).with_name("rate_limiter.lua")

lua_script = LUA_SCRIPT_PATH.read_text()

script_hash = redis_client.script_load(lua_script)

async def check_request(request: Request, call_next):  

    path = request.url.path

    if path in ["/docs", "/openapi.json", "/redoc", "/favicon.ico"]:
        return await call_next(request)
    
    elif path.startswith("/api/users"):
        policy = "auth"
        capacity = BUCKET_CAPACITY_AUTH
        fill_rate = TOKEN_FILL_RATE_AUTH
    
    elif path.startswith("/api/urls") or path.startswith("/api/analytics") or path == "/":
        policy = "api"
        capacity = BUCKET_CAPACITY_API
        fill_rate = TOKEN_FILL_RATE_API
    
    else:
        policy = "redirect"
        capacity = BUCKET_CAPACITY_REDIRECT
        fill_rate = TOKEN_FILL_RATE_REDIRECT
    

    client_ip = request.client.host
    prefix = "rate_limiter:" + policy + f":{client_ip}"

    keys = [prefix + ":tokens", prefix+":timestamp"]
    args = [capacity,fill_rate,datetime.now(UTC).timestamp()]
    allowed, new_tokens = redis_client.evalsha(script_hash,len(keys),*keys, *args)

    retry_after = math.ceil(1/fill_rate)

    if allowed:
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(math.floor(float(new_tokens)))
        return response

    return Response(
            content="Too many requests",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="text/plain",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": str(retry_after)}
        )

    
    