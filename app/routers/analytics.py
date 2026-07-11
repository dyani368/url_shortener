from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import ShortUrl, User
from app.schemas.url_schema import UrlAnalyticsResponse

router = APIRouter()

@router.get("/{url_id}", response_model=UrlAnalyticsResponse)
def get_analytics(url_id: int, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):

    url = db.execute(select(ShortUrl).where(ShortUrl.id == url_id, ShortUrl.user_id == current_user.id)).scalars().first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="url does not exist")

    return url

