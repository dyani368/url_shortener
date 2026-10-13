from sqlalchemy import update, func
import logging
from app.core.database import SessionLocal
from app.models import ShortUrl

logger = logging.getLogger(__name__)

async def calculate_analytics(url_id: int):

    async with SessionLocal() as db:
        try:
            await db.execute(
                update(ShortUrl)
                .where(ShortUrl.id == url_id)
                .values(
                    click_count=ShortUrl.click_count + 1,
                    last_clicked_at=func.now(),
                )
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to record click for URL id %s", url_id)
