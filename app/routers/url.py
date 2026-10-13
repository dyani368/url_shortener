from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from app.schemas.url_schema import UrlResponse, UrlCreate
from app.models import ShortUrl, User
from app.core.database import get_db
from app.core.security import get_current_user
from app.utils import shortener
from app.cache import redis

from sqlalchemy.exc import IntegrityError
from redis.exceptions import RedisError

router = APIRouter()

@router.post(
    "",
    response_model=UrlResponse,
    status_code=status.HTTP_201_CREATED)
async def create_short_url(url: UrlCreate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):

    for _ in range(5):
        short_code = shortener.generate_short_code()
        res = await db.execute(select(ShortUrl).where(ShortUrl.short_code==short_code))
        db_short = res.scalars().first()
        if not db_short:
            new_url = ShortUrl(long_url=str(url.long_url), short_code=short_code, user_id=current_user.id)
            db.add(new_url)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                collision = await db.execute(select(ShortUrl.id).where(ShortUrl.short_code == short_code))
                if collision.scalar_one_or_none() is not None:
                    continue
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Could not create short URL",
                )

            await db.refresh(new_url)
            return new_url

    raise HTTPException(status_code=503, detail="Could not allocate a short code; retry")

@router.get("", response_model=list[UrlResponse])
async def get_url_list(current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession , Depends(get_db)]):
    res = await db.execute(select(ShortUrl).where(ShortUrl.user_id==current_user.id))
    url_list = res.scalars().all()

    return url_list

@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(url_id: int, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    res = await db.execute(select(ShortUrl).where(ShortUrl.id == url_id, ShortUrl.user_id == current_user.id))
    url = res.scalars().first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Url not found")
    
    # Invalidate both sides of the commit so an in-flight cache miss cannot
    # repopulate a redirect just before the database row is removed.
    try:
        await redis.delete_cached_url(url.short_code)
    except RedisError:
        pass
    await db.delete(url)
    await db.commit()
    try:
        await redis.delete_cached_url(url.short_code)
    except RedisError:
        # The stale entry is bounded by the URL expiry TTL. Do not turn a
        # successful database deletion into a failed API response.
        pass






