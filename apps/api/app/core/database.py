"""
PathForge API — Database Engine & Session Management
=====================================================
Async SQLAlchemy engine with production-grade connection pooling.

Features (Sprint 29):
- Connection pool with recycle (stale connection prevention)
- Pre-ping with timeout (fast-fail on unresponsive DB)
- Conditional SSL for Supabase production

Usage:
    from app.core.database import get_db

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db_ssl import build_connect_args

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=settings.database_pool_recycle,
    pool_timeout=settings.database_pool_timeout,
    # Use the narrowed property (ADR-0001) so a future `None` leak trips an
    # AssertionError at boot rather than silently degrading TLS to off.
    connect_args=build_connect_args(settings.database_ssl_enabled),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
