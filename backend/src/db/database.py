from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config import get_settings

_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialize database engine and create tables."""
    global _engine, _session_factory
    from db.models import Base

    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Enable WAL mode for concurrent reads
    async with _engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))


async def close_db() -> None:
    """Close database engine."""
    global _engine
    if _engine:
        await _engine.dispose()


async def get_session() -> AsyncSession:
    """Get a database session. Used as FastAPI dependency."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    """Get a database session as async context manager (for use outside FastAPI DI)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session
