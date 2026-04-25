"""
PathForge — Career Command Center™ Models
==========================================
Domain models for the Unified Career Command Center — the industry's
first consumer-facing dashboard that aggregates 12 AI intelligence
engines into a single career health monitoring system.

Models:
    CareerSnapshot             — Cached aggregate career health view
    CommandCenterPreference    — User display preferences

Enums:
    HealthBand        — thriving | healthy | attention | at_risk | critical
    TrendDirection    — improving | stable | declining
    HeartbeatStatus   — active | stale | dormant | never_run

Proprietary Innovations:
    🔥 Career Vitals™         — 12-signal composite health score (0-100)
    🔥 Engine Heartbeat™      — Real-time engine freshness monitoring
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.career_dna import CareerDNA
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class HealthBand(enum.StrEnum):
    """Career Health Score band classification (0-100 scale)."""

    THRIVING = "thriving"      # 80-100: Maintain momentum
    HEALTHY = "healthy"        # 60-79:  Minor tune-ups
    ATTENTION = "attention"    # 40-59:  Review flagged areas
    AT_RISK = "at_risk"        # 20-39:  Immediate action needed
    CRITICAL = "critical"      # 0-19:   Complete review recommended


class TrendDirection(enum.StrEnum):
    """Career health trend direction between snapshots."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class HeartbeatStatus(enum.StrEnum):
    """Engine data freshness indicator (Engine Heartbeat™)."""

    ACTIVE = "active"          # Analyzed within 7 days
    STALE = "stale"            # 8-30 days ago
    DORMANT = "dormant"        # 30+ days ago
    NEVER_RUN = "never_run"    # No analysis exists


# ── CareerSnapshot ─────────────────────────────────────────────


class CareerSnapshot(Base, UUIDMixin, TimestampMixin):
    """Career Command Center™ — Career Vitals™ Snapshot.

    Cached aggregate of all 12 engine statuses, computed via
    the Career Vitals™ weighted composite algorithm. Each snapshot
    captures the complete career health state at a point in time.

    Career Health Score = Σ(engine_weight × engine_health) / Σ engine_weight

    Engine Health = f(recency, score, trend):
        - recency:  0-100 based on days since last analysis
        - score:    0-100 from engine's native scoring
        - trend:    +10 improving, 0 stable, -10 declining
    """

    __tablename__ = "cc_career_snapshots"
    __table_args__ = (
        CheckConstraint(
            "health_score >= 0.0 AND health_score <= 100.0",
            name="ck_cc_snapshot_health_score_range",
        ),
    )

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Career Vitals™ composite score ──
    health_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    health_band: Mapped[str] = mapped_column(
        String(20), default=HealthBand.ATTENTION.value,
        server_default="attention", nullable=False,
    )

    # ── Engine status map (12 engines) ──
    engine_statuses: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Strengths & attention areas ──
    strengths: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    attention_areas: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Trend direction ──
    trend_direction: Mapped[str] = mapped_column(
        String(20), default=TrendDirection.STABLE.value,
        server_default="stable", nullable=False,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="Career Vitals™ — 12-engine composite health score",
        server_default="Career Vitals™ — 12-engine composite health score",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Career Health Score is an AI-generated composite metric "
            "derived from 12 intelligence engines. It reflects career "
            "wellness indicators, not guaranteed outcomes. Use alongside "
            "your own judgment."
        ),
        server_default=(
            "Career Health Score is an AI-generated composite metric "
            "derived from 12 intelligence engines. It reflects career "
            "wellness indicators, not guaranteed outcomes. Use alongside "
            "your own judgment."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship("CareerDNA")
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CareerSnapshot(score={self.health_score}, "
            f"band={self.health_band}, trend={self.trend_direction})>"
        )


# ── CommandCenterPreference ────────────────────────────────────


class CommandCenterPreference(Base, UUIDMixin, TimestampMixin):
    """User display preferences for Career Command Center™.

    Controls which engines are pinned (shown first) or hidden
    from the unified dashboard view.
    """

    __tablename__ = "cc_preferences"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Preference fields ──
    pinned_engines: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    hidden_engines: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CommandCenterPreference(user_id={self.user_id}, "
            f"pinned={self.pinned_engines})>"
        )
