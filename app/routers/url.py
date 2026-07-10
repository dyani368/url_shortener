from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated

from app.schemas.url_schema import UrlResponse, UrlCreate
from app.models import ShortUrl, User
from app.core.database import get_db
from app.core.security import get_current_user
from app.utils import shortener
from app.cache import redis

from sqlalchemy.exc import IntegrityError

router = APIRouter()

@router.post(
    "",
    response_model=UrlResponse,
    status_code=status.HTTP_201_CREATED)
def create_short_url(url: UrlCreate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):

    while True:
        short_code = shortener.generate_short_code()
        db_short = db.execute(select(ShortUrl).where(ShortUrl.short_code==short_code)).scalars().first()    
        if not db_short:
            break
    
    url = ShortUrl(long_url=str(url.long_url), short_code = short_code, user_id = current_user.id)
    db.add(url)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate entry",
        )

    db.refresh(url)
    return url

@router.get("", response_model=list[UrlResponse])
def get_url_list(current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session , Depends(get_db)]):
    url_list = db.execute(select(ShortUrl).where(ShortUrl.user_id==current_user.id)).scalars().all()

    return url_list

@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(url_id: int, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    url = db.execute(select(ShortUrl).where(ShortUrl.id == url_id, ShortUrl.user_id == current_user.id)).scalars().first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Url not found")
    
    redis.delete_cached_url(url.short_code)    
    db.delete(url)
    db.commit()






