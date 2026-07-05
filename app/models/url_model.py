from __future__ import annotations
from datetime import datetime,timedelta, UTC
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class ShortUrl(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    long_url: Mapped[str]=mapped_column(nullable=False)
    short_code: Mapped[str]=mapped_column(unique=True,nullable=False)
    click_count: Mapped[int]=mapped_column(default=0, nullable= False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(UTC))
    last_clicked_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True),default=None)
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(UTC)+timedelta(days=30))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    user: Mapped["User"] = relationship(back_populates="urls_created")
