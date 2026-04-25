"""
PathForge — Cross-Engine Recommendation Intelligence™ Models
==============================================================
Domain models for the Cross-Engine Recommendation Intelligence
system — the industry's first individual-facing multi-engine
recommendation fusion pipeline that correlates insights from
all 12 AI intelligence engines into prioritized, actionable
career recommendations.

Models:
    CrossEngineRecommendation    — Individual recommendation with priority scoring
    RecommendationCorrelation    — Engine-to-recommendation contribution mapping
    RecommendationBatch          — Groups recommendations from a single analysis run
    RecommendationPreference     — User preference for recommendation filtering

Enums:
    RecommendationType  — skill_gap | threat_mitigation | opportunity | ...
    RecommendationStatus — pending | in_progress | completed | dismissed | expired
    EffortLevel          — quick_win | moderate | significant | major_initiative

Proprietary Innovations:
    🔥 Intelligence Fusion Engine™  — Multi-engine signal correlation
    🔥 Priority-Weighted Score™     — urgency × impact × inverse_effort
    🔥 Cross-Engine Correlation Map™ — Per-recommendation engine attribution
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class RecommendationType(enum.StrEnum):
    """Category of cross-engine recommendation."""

    SKILL_GAP = "skill_gap"                        # Skill gap identified across engines
    THREAT_MITIGATION = "threat_mitigation"         # Threat Radar-driven risk response
    OPPORTUNITY = "opportunity"                     # New career opportunity detected
    SALARY_OPTIMIZATION = "salary_optimization"     # Compensation improvement path
    CAREER_ACCELERATION = "career_acceleration"     # Fast-track career growth actions
    NETWORK_BUILDING = "network_building"           # Network expansion recommendations


class RecommendationStatus(enum.StrEnum):
    """Lifecycle status of a recommendation."""

    PENDING = "pending"            # Generated but not yet acted upon
    IN_PROGRESS = "in_progress"    # User has started working on it
    COMPLETED = "completed"        # User marked as completed
    DISMISSED = "dismissed"        # User dismissed without action
    EXPIRED = "expired"            # Recommendation is no longer relevant


class EffortLevel(enum.StrEnum):
    """Estimated effort required to act on a recommendation."""

    QUICK_WIN = "quick_win"                # < 1 hour, easy win
    MODERATE = "moderate"                  # 1-4 hours, manageable effort
    SIGNIFICANT = "significant"            # 1-2 weeks, sustained effort
    MAJOR_INITIATIVE = "major_initiative"  # 1+ month, major undertaking


# ── CrossEngineRecommendation ─────────────────────────────────


class CrossEngineRecommendation(Base, UUIDMixin, TimestampMixin):
    """Cross-Engine Recommendation Intelligence™ — Individual Recommendation.

    Each recommendation is synthesized from multiple intelligence engine
    signals and scored using the Priority-Weighted Score™ algorithm:

    Priority Score = urgency (0.40) × impact (0.35) × inverse_effort (0.25)

    All scores are capped at MAX_CONFIDENCE = 0.85 to prevent
    overconfidence in AI-generated career guidance.
    """

    __tablename__ = "ri_recommendations"
    __table_args__ = (
        CheckConstraint(
            "priority_score >= 0.0 AND priority_score <= 100.0",
            name="ck_ri_rec_priority_score_range",
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 0.85",
            name="ck_ri_rec_confidence_cap",
        ),
    )

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("ri_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Core fields ──
    recommendation_type: Mapped[str] = mapped_column(
        String(40), default=RecommendationType.OPPORTUNITY.value,
        server_default="opportunity", nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RecommendationStatus.PENDING.value,
        server_default="pending", nullable=False, index=True,
    )
    effort_level: Mapped[str] = mapped_column(
        String(30), default=EffortLevel.MODERATE.value,
        server_default="moderate", nullable=False,
    )

    # ── Priority scoring ──
    priority_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    urgency: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    impact_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Content fields ──
    title: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    action_items: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Source engine context ──
    source_engines: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="Intelligence Fusion Engine™ — cross-engine recommendation",
        server_default="Intelligence Fusion Engine™ — cross-engine recommendation",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This recommendation is AI-generated by correlating signals "
            "from multiple intelligence engines. Priority scores are "
            "estimates, not guarantees. Use alongside your own judgment."
        ),
        server_default=(
            "This recommendation is AI-generated by correlating signals "
            "from multiple intelligence engines. Priority scores are "
            "estimates, not guarantees. Use alongside your own judgment."
        ),
        nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    correlations: Mapped[list[RecommendationCorrelation]] = relationship(
        "RecommendationCorrelation",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CrossEngineRecommendation(type={self.recommendation_type}, "
            f"priority={self.priority_score}, status={self.status})>"
        )


# ── RecommendationCorrelation ────────────────────────────────


class RecommendationCorrelation(Base, UUIDMixin, TimestampMixin):
    """Cross-Engine Correlation Map™ — Engine Contribution Mapping.

    Maps which intelligence engines contributed to a recommendation
    and with what correlation strength. Enables per-recommendation
    transparency into the Intelligence Fusion Engine™ pipeline.
    """

    __tablename__ = "ri_correlations"
    __table_args__ = (
        CheckConstraint(
            "correlation_strength >= 0.0 AND correlation_strength <= 1.0",
            name="ck_ri_corr_strength_range",
        ),
    )

    # ── Foreign keys ──
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("ri_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    engine_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    correlation_strength: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    insight_summary: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )

    # ── Relationships ──
    recommendation: Mapped[CrossEngineRecommendation] = relationship(
        "CrossEngineRecommendation",
        back_populates="correlations",
    )

    def __repr__(self) -> str:
        return (
            f"<RecommendationCorrelation(engine={self.engine_name}, "
            f"strength={self.correlation_strength})>"
        )


# ── RecommendationBatch ──────────────────────────────────────


class RecommendationBatch(Base, UUIDMixin, TimestampMixin):
    """Intelligence Fusion Engine™ — Recommendation Generation Batch.

    Groups recommendations generated from a single analysis run.
    Captures the engine snapshot at generation time for audit
    trail and reproducibility.
    """

    __tablename__ = "ri_batches"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Batch context ──
    batch_type: Mapped[str] = mapped_column(
        String(40), default="manual",
        server_default="manual", nullable=False,
    )
    engine_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    total_recommendations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    career_vitals_at_generation: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="Intelligence Fusion Engine™ — batch analysis run",
        server_default="Intelligence Fusion Engine™ — batch analysis run",
        nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<RecommendationBatch(type={self.batch_type}, "
            f"count={self.total_recommendations}, "
            f"vitals={self.career_vitals_at_generation})>"
        )


# ── RecommendationPreference ────────────────────────────────


class RecommendationPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Recommendation Intelligence™ filtering.

    Controls which recommendation categories are enabled, minimum
    priority threshold, and maximum recommendations per batch.
    """

    __tablename__ = "ri_preferences"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Preference fields ──
    enabled_categories: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    min_priority_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    max_recommendations_per_batch: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10,
    )
    preferred_effort_levels: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<RecommendationPreference(user_id={self.user_id}, "
            f"min_priority={self.min_priority_threshold}, "
            f"max_per_batch={self.max_recommendations_per_batch})>"
        )
