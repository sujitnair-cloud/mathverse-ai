import asyncio
import sys
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


async def init_db(retries: int = 6, delay: float = 2.0):
    """
    A just-provisioned Postgres plugin's internal DNS name (e.g.
    postgres.railway.internal) can take a short while to become resolvable
    on the platform's internal network — this crashed production outright
    (socket.gaierror: Name or service not known) on the very first deploy
    after adding the database, immediately at startup, before the app ever
    got a chance to serve a single request. Retry with backoff instead of
    treating "not reachable yet" as fatal; only give up after genuinely
    exhausting the window a slow-to-appear database would need.
    """
    from app.models import models  # noqa: F401
    last_error: Exception = RuntimeError("init_db: no attempt was made")
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            last_error = e
            if attempt < retries:
                print(
                    f"[MathVerse] Database not reachable yet (attempt {attempt}/{retries}): "
                    f"{e}. Retrying in {delay:.1f}s...",
                    file=sys.stderr,
                )
                await asyncio.sleep(delay)
                delay *= 1.6
    raise last_error
