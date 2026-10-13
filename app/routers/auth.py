from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from fastapi.security import OAuth2PasswordRequestForm

from app.models import User
from app.schemas import user_schema
from app.core.database import get_db
from app.core import security 

from sqlalchemy.exc import IntegrityError

router = APIRouter()

@router.post("/register", response_model=user_schema.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(new_user: user_schema.UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    res1 = await db.execute(select(User).where(User.username == new_user.username))
    result1 = res1.scalars().first()

    if result1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already registered")
    
    res2 = await db.execute(select(User).where(User.email == new_user.email))
    result2 = res2.scalars().first()

    if result2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    user = User(username=new_user.username, email=new_user.email, hashed_password=security.hash_password(new_user.password))
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    await db.refresh(user)
    return user

@router.post("/token", response_model=user_schema.Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[AsyncSession, Depends(get_db)]):

    res = await db.execute(select(User).where(User.username==form_data.username))
    result1 = res.scalars().first()
    
    if not result1 or not security.verify_password(form_data.password,result1.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    data = {
        "sub" : str(result1.id)
    }

    token = security.create_access_token(data)

    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=user_schema.UserResponse)
async def get_me(current_user: Annotated[User, Depends(security.get_current_user)]):
    return current_user

    



    



