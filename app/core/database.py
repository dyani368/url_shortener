from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Replace driver prefix for asyncpg if using standard postgresql://
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

parsed = urlparse(database_url)
query_params = parse_qs(parsed.query)
query_params.pop("channel_binding", None)
if "sslmode" in query_params:
    val = query_params.pop("sslmode")
    query_params["ssl"] = val

new_query = urlencode(query_params, doseq=True)
database_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

engine = create_async_engine(
    database_url,
    pool_pre_ping=True
)

SessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as db:
        yield db
