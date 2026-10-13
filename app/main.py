from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from datetime import datetime, UTC
import logging
import math
from sqlalchemy import select
from redis.exceptions import RedisError

from app.core.database import SessionLocal
from app.models import ShortUrl
from app.routers import auth, url, analytics
from app.cache import redis
from app.services import analytics_service
from app.middleware import rate_limiter
from pathlib import Path

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await redis.redis_client.aclose()
    from app.core.database import engine
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router,prefix="/api/users", tags=["users"])
app.include_router(url.router,prefix="/api/urls", tags=["urls"])
app.include_router(analytics.router,prefix="/api/analytics", tags=["analytics"])

app.middleware("http")(rate_limiter.check_request)


@app.get("/health/live", include_in_schema=False)
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def readiness():
    try:
        await redis.redis_client.ping()
        from app.core.database import engine
        async with engine.connect() as connection:
            await connection.execute(select(1))
    except Exception as exc:
        logger.warning("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="service unavailable") from exc
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/static/{asset_path:path}", include_in_schema=False)
async def frontend_assets(asset_path: str):
    asset = (FRONTEND_DIR / asset_path).resolve()
    if FRONTEND_DIR.resolve() not in asset.parents or not asset.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset)

@app.get("/{short_code}")
async def redirect(short_code: str, background_tasks: BackgroundTasks):
    try:
        cached_value = await redis.get_cache_value(short_code)
    except RedisError:
        logger.warning("Redis cache unavailable; looking up redirect in database")
        cached_value = None

    if cached_value:
        background_tasks.add_task(analytics_service.calculate_analytics, cached_value["id"])
        return RedirectResponse(url=cached_value["long_url"])

    async with SessionLocal() as db:
        res = await db.execute(select(ShortUrl).where(ShortUrl.short_code == short_code))
        url = res.scalars().first()

        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="url not found")

        expiry_date = url.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        if expiry_date <= now:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="url expired")

        ttl_seconds = (expiry_date - now).total_seconds()
        try:
            await redis.set_cache_value(short_code, url.long_url, url.id, math.ceil(ttl_seconds))
        except RedisError:
            logger.warning("Redis cache unavailable; redirect served without caching")

        background_tasks.add_task(analytics_service.calculate_analytics, url.id)

        return RedirectResponse(url=url.long_url)
