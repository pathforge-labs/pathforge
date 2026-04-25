"""
PathForge — CLI Management Commands
======================================
Sprint 34: Admin promotion and management utilities.

Usage:
    python -m app.cli promote_admin <email>
    python -m app.cli list_admins

F18: Entry point with `if __name__` guard.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User, UserRole


async def _get_session() -> AsyncSession:
    """Create a standalone async session for CLI operations."""
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


async def promote_admin(email: str) -> None:
    """Promote a user to admin role."""
    session = await _get_session()

    try:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if user is None:
                print(f"Error: User with email '{email}' not found.")
                return

            if user.role == UserRole.ADMIN:
                print(f"User '{email}' is already an admin.")
                return

            user.role = UserRole.ADMIN
            print(f"Successfully promoted '{email}' to admin.")
    finally:
        await session.close()


async def list_admins() -> None:
    """List all admin users."""
    session = await _get_session()

    try:
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        admins = result.scalars().all()

        if not admins:
            print("No admin users found.")
            return

        print(f"Admin users ({len(list(admins))}):")
        for admin in admins:
            print(f"  - {admin.email} (id={admin.id})")
    finally:
        await session.close()


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.cli promote_admin <email>")
        print("  python -m app.cli list_admins")
        sys.exit(1)

    command = sys.argv[1]

    if command == "promote_admin":
        if len(sys.argv) < 3:
            print("Error: email argument required")
            sys.exit(1)
        asyncio.run(promote_admin(sys.argv[2]))
    elif command == "list_admins":
        asyncio.run(list_admins())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
