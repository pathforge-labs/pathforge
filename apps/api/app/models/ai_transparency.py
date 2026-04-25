"""
PathForge — AI Transparency Record Model
==========================================
Persistence layer for the AI Trust Layer™.

Stores transparency records in the database alongside the in-memory
circular buffer, enabling durable audit trails and production-grade
explainability queries.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AITransparencyRecord(Base, UUIDMixin, TimestampMixin):
    """Persistent AI analysis transparency record.

    Each row represents a single AI analysis with full explainability
    metadata — confidence score, data sources, token usage, and latency.
    Records are linked to users via user_id for GDPR compliance
    (deletion cascades handled by FK).
    """

    __tablename__ = "ai_transparency_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        server_default="",
    )
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="primary",
    )
    confidence_score: Mapped[float] = mapped_column(
        Float(),
        nullable=False,
        server_default="0.0",
    )
    confidence_label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="Low",
    )
    data_sources: Mapped[list[str]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="[]",
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    success: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        server_default="true",
    )
    retries: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        server_default="0",
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_ai_transparency_user_type", "user_id", "analysis_type"),
        Index("ix_ai_transparency_created_at", "created_at"),
    )
