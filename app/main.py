from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated

from app.core.database import get_db
from app.models import ShortUrl
from app.routers import auth, url


app = FastAPI()
app.include_router(auth.router,prefix="/api/users", tags=["users"])
app.include_router(url.router,prefix="/api/urls", tags=["urls"])


@app.get("/")
def home():
    return {"message":"Welcome to URL Shortener!"}

@app.get("/{short_code}")
def redirect(short_code: str, db: Annotated[Session, Depends(get_db)]):

    url = db.execute(select(ShortUrl).where(ShortUrl.short_code == short_code)).scalars().first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="url not found")

    expiry_date = url.expiry_date
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    if expiry_date < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="url expired")

    return RedirectResponse(url=url.long_url)
