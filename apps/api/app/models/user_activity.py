"""
PathForge — User Activity Log Model
======================================
Sprint 36 WS-6 / Audit F24: Lightweight model for tracking user-initiated
actions, distinct from AdminAuditLog (which requires admin_user_id).

Examples: target_role_update, career_dna_refresh, settings_change
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserActivityLog(Base):
    """Audit trail for user-initiated actions."""

    __tablename__ = "user_activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Action identifier (e.g., target_role_update)",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Entity type (e.g., growth_vector, career_dna)",
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        doc="Optional ID of the affected entity",
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional context (e.g., previous/new values)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<UserActivityLog(action={self.action!r}, "
            f"entity_type={self.entity_type!r})>"
        )
