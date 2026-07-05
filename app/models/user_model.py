from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int]=mapped_column(primary_key=True, index=True)
    username: Mapped[str]=mapped_column(unique=True,nullable=False)
    email: Mapped[str]=mapped_column(unique=True,nullable=False)
    hashed_password: Mapped[str]=mapped_column(nullable=False)

    urls_created : Mapped[list["ShortUrl"]] = relationship(back_populates="user", cascade="all, delete-orphan")