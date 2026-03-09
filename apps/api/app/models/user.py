"""
PathForge — User Model
=======================
Platform user account with authentication fields.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.career_dna import CareerDNA
    from app.models.preference import Preference
    from app.models.resume import Resume
    from app.models.subscription import Subscription
    from app.models.token_blacklist import BlacklistEntry


# Sprint 34: User role for RBAC (F24: StrEnum pattern)
class UserRole(enum.StrEnum):
    """User access level classification."""

    USER = "user"
    ADMIN = "admin"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(50), default="email", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sprint 39: Email verification
    verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sprint 34: RBAC role (D3)
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER.value, server_default="user",
        nullable=False, index=True,
    )

    # Relationships
    resumes: Mapped[list[Resume]] = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[list[Preference]] = relationship(
        "Preference", back_populates="user", cascade="all, delete-orphan"
    )
    blacklist_entries: Mapped[list[BlacklistEntry]] = relationship(
        "BlacklistEntry", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    career_dna: Mapped[CareerDNA | None] = relationship(
        "CareerDNA", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    # Sprint 34: Billing (F36: eager loading support)
    subscription: Mapped[Subscription | None] = relationship(
        "Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
