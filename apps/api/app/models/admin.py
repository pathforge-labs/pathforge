"""
PathForge — Admin Audit Log Model
====================================
Sprint 34: Admin action tracking for RBAC audit trail.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class AdminAuditLog(UUIDMixin, TimestampMixin, Base):
    """
    Immutable record of admin actions for RBAC audit trail.

    Every admin action (user updates, subscription overrides, promotions)
    creates a log entry with the acting admin, target user, and details.
    """

    __tablename__ = "admin_audit_logs"

    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    details: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AdminAuditLog admin={self.admin_user_id} action={self.action}>"
