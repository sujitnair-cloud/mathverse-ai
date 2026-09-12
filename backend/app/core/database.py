from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


def _make_engine():
    url = settings.async_database_url
    if url.startswith("sqlite"):
        # SQLite: no pool_size / max_overflow — uses StaticPool by default
        return create_async_engine(url, echo=settings.DEBUG)
    # PostgreSQL: explicit pool sizing for production load
    return create_async_engine(
        url,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,  # drop and reconnect stale connections
        pool_recycle=1800,   # recycle connections every 30 min
    )


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    from app.models import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
