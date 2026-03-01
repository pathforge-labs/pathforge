"""
PathForge — Push Token Model
==============================
Device push token storage for mobile push notification delivery.

Each user can have multiple tokens (one per device). Tokens are
validated against Expo Push Token format and deactivated on
permanent delivery failure (HTTP 410).

Audit Finding #2: Separate model from NotificationPreference to
maintain single-responsibility — preferences control *what* to
send, tokens control *where* to send.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class PushToken(Base, UUIDMixin, TimestampMixin):
    """Device push token for mobile notification delivery.

    Lifecycle: registered → active → (deactivated on 410 | logout)

    Constraints:
        - Unique device_token prevents duplicate registrations.
        - Composite index (user_id, is_active) optimises active
          token lookup during dispatch.
    """

    __tablename__ = "push_tokens"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Token fields ──
    device_token: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True,
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )

    # ── State ──
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    # ── Indexes ──
    __table_args__ = (
        Index("ix_push_tokens_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<PushToken(platform={self.platform}, "
            f"active={self.is_active})>"
        )
