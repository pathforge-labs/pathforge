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

import ssl
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _build_connect_args() -> dict[str, Any]:
    """Build asyncpg connect_args, including SSL if configured."""
    connect_args: dict[str, Any] = {}
    if settings.database_ssl:
        ssl_context = ssl.create_default_context()
        # Supabase uses valid certs — verify by default
        connect_args["ssl"] = ssl_context
    return connect_args


engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=settings.database_pool_recycle,
    pool_timeout=settings.database_pool_timeout,
    connect_args=_build_connect_args(),
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
