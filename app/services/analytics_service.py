from sqlalchemy import select
from datetime import datetime, UTC
from app.core.database import SessionLocal
from app.models import ShortUrl

def calculate_analytics(url_id: int):

    db = SessionLocal()
    try:
        url = db.execute(select(ShortUrl).where(ShortUrl.id == url_id)).scalars().first()

        if not url:
            return

        url.click_count += 1
        url.last_clicked_at = datetime.now(UTC)

        db.commit()
    except Exception:
        db.rollback()
        print("Failed to update analytics")
    finally:
        db.close()
