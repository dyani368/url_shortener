from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated
from app.core.database import get_db

from app.models.user_model import User

# User registers:
# get email/password
# hash password
# store the hash

# User logs in :
# receive email/password
# check if user exists
# verify password
# create a jwt 
# return token 

# protecting endpoint:
# read the token 
# verify the token 
# get user id
# get user from db
# return current user

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")

def hash_password(password: str):
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str):
    return password_hash.verify(password,hashed_password)

def create_access_token(data: dict, expires_delta: timedelta|None = None):
    to_encode = data.copy()

    if expires_delta:
        expiry = datetime.now(timezone.utc) + expires_delta
    else:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp":expiry})

    token = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
        )

    return token 

def verify_token(token: str) -> int|None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm]
        )

        user_id: str|None  = payload.get("sub")
        if user_id is None:
            return None

        return int(user_id)
    
    except (jwt.InvalidTokenError, ValueError):
        return None

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.execute(select(User).where(User.id == user_id)).scalars().first()

    if not user:
        raise credentials_exception
    
    return user
