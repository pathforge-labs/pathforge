"""
PathForge — Skill Decay & Growth Tracker Models
==================================================
Domain models for the Skill Decay & Growth Tracker — the industry's
first consumer-grade skill freshness intelligence system.

Models:
    1. SkillFreshness — Exponential decay scoring per skill
    2. MarketDemandSnapshot — Point-in-time market demand per skill
    3. SkillVelocityEntry — Individual skill velocity tracking
    4. ReskillingPathway — Personalized learning recommendations
    5. SkillDecayPreference — User notification preferences

Proprietary Innovations:
    - Skill Half-Life Engine™ (category-calibrated exponential decay)
    - Market Demand Curves™ (per-skill trend lines with growth projections)
    - Skill Velocity Map™ (individual-level acceleration tracking)
    - Personalized Reskilling Pathways™ (AI-generated learning plans)
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.career_dna import CareerDNA
    from app.models.user import User

# ── Enums ──────────────────────────────────────────────────────


class DecayRate(enum.StrEnum):
    """Skill decay speed classification (calibrated per skill category)."""

    FAST = "fast"           # Technical/tool skills: ~2.5yr half-life
    MODERATE = "moderate"   # Domain skills: ~4yr half-life
    SLOW = "slow"           # Soft/language skills: ~7yr half-life
    STABLE = "stable"       # Foundational skills: minimal decay


class DemandTrend(enum.StrEnum):
    """Market demand trajectory for a specific skill."""

    SURGING = "surging"         # >25% YoY growth in job postings
    GROWING = "growing"         # 5-25% YoY growth
    STABLE = "stable"           # -5% to +5% YoY
    DECLINING = "declining"     # -5% to -25% YoY
    OBSOLESCENT = "obsolescent"  # >25% YoY decline


class VelocityDirection(enum.StrEnum):
    """Individual skill velocity classification."""

    ACCELERATING = "accelerating"  # Freshness + demand both rising
    STEADY = "steady"              # Stable across both factors
    DECELERATING = "decelerating"  # Either freshness or demand dropping
    STALLED = "stalled"            # Both freshness and demand declining


class PathwayPriority(enum.StrEnum):
    """Reskilling pathway urgency classification."""

    CRITICAL = "critical"       # Skill at risk + high market demand
    RECOMMENDED = "recommended"  # Beneficial for career growth
    OPTIONAL = "optional"       # Nice-to-have, low urgency


# ── SkillFreshness ─────────────────────────────────────────────


class SkillFreshness(UUIDMixin, TimestampMixin, Base):
    """
    Skill Half-Life Engine™ — exponential decay scoring per skill.

    Formula: freshness = 100 × exp(-λ × days_since_active)
    where λ = ln(2) / half_life_days

    Half-life calibration (WEF research-aligned):
        - Technical skills: 912 days (~2.5 years)
        - Tool skills: 1095 days (~3 years)
        - Domain skills: 1460 days (~4 years)
        - Soft skills: 2555 days (~7 years)
        - Language skills: 3650 days (~10 years)

    Explainability: every score includes LLM analysis_reasoning.
    """

    __tablename__ = "skill_freshness"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="technical", nullable=False
    )
    last_active_date: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    freshness_score: Mapped[float] = mapped_column(
        Float, default=100.0, nullable=False
    )
    half_life_days: Mapped[int] = mapped_column(
        Integer, default=912, nullable=False
    )
    decay_rate: Mapped[str] = mapped_column(
        String(20), default=DecayRate.MODERATE.value, nullable=False
    )
    days_since_active: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    refresh_urgency: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    analysis_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="skill_freshness"
    )

    def __repr__(self) -> str:
        return (
            f"<SkillFreshness {self.skill_name} "
            f"score={self.freshness_score:.0f}>"
        )


# ── MarketDemandSnapshot ───────────────────────────────────────


class MarketDemandSnapshot(UUIDMixin, TimestampMixin, Base):
    """
    Market Demand Curves™ — point-in-time market demand per skill.

    Combines PathForge job listing data with LLM-powered market
    intelligence to generate personalized demand curves and
    6-month / 12-month growth projections.

    Confidence capped at 0.85 (inherent uncertainty principle).
    """

    __tablename__ = "market_demand_snapshots"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    demand_score: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    demand_trend: Mapped[str] = mapped_column(
        String(20), default=DemandTrend.STABLE.value, nullable=False
    )
    trend_confidence: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )
    job_posting_signal: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    industry_relevance: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    growth_projection_6m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    growth_projection_12m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    data_sources: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="market_demand_snapshots"
    )

    def __repr__(self) -> str:
        return (
            f"<MarketDemandSnapshot {self.skill_name} "
            f"demand={self.demand_score:.0f} ({self.demand_trend})>"
        )


# ── SkillVelocityEntry ─────────────────────────────────────────


class SkillVelocityEntry(UUIDMixin, TimestampMixin, Base):
    """
    Skill Velocity Map™ — individual-level skill velocity tracking.

    Composite formula:
        velocity_score = (freshness_component × 0.4)
                       + (demand_component × 0.4)
                       + (acceleration × 0.2)

    Positive velocity = skill is growing in both freshness and demand.
    Negative velocity = skill is declining — reskilling path recommended.

    Composite health = normalized 0-100 overall skill health metric.
    """

    __tablename__ = "skill_velocity_entries"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    velocity_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    velocity_direction: Mapped[str] = mapped_column(
        String(20), default=VelocityDirection.STEADY.value, nullable=False
    )
    freshness_component: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    demand_component: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    composite_health: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    acceleration: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="skill_velocity_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<SkillVelocityEntry {self.skill_name} "
            f"v={self.velocity_score:.1f} ({self.velocity_direction})>"
        )


# ── ReskillingPathway ──────────────────────────────────────────


class ReskillingPathway(UUIDMixin, TimestampMixin, Base):
    """
    Personalized Reskilling Pathways™ — AI-generated learning plans.

    Every pathway includes:
        - Target skill with current→target level progression
        - Estimated effort in hours
        - Prerequisite skills check
        - Curated learning resources
        - Career impact statement
        - Projected freshness gain and demand alignment

    Design principle: pathways empower, never prescribe.
    Users always see 2-3 options, never a single mandate.
    """

    __tablename__ = "reskilling_pathways"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_skill: Mapped[str] = mapped_column(String(255), nullable=False)
    current_level: Mapped[str] = mapped_column(
        String(50), default="beginner", nullable=False
    )
    target_level: Mapped[str] = mapped_column(
        String(50), default="intermediate", nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default=PathwayPriority.RECOMMENDED.value, nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_effort_hours: Mapped[int] = mapped_column(
        Integer, default=40, nullable=False
    )
    prerequisite_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    learning_resources: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    career_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness_gain: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    demand_alignment: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="reskilling_pathways"
    )

    def __repr__(self) -> str:
        return (
            f"<ReskillingPathway {self.target_skill} "
            f"[{self.priority}] {self.current_level}→{self.target_level}>"
        )


# ── SkillDecayPreference ───────────────────────────────────────


class SkillDecayPreference(UUIDMixin, TimestampMixin, Base):
    """
    User notification preferences for the Skill Decay & Growth Tracker.

    Supports user autonomy (PathForge Manifesto #5):
    users control alert thresholds, notification frequency,
    and which skill categories to track.
    """

    __tablename__ = "skill_decay_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notification_frequency: Mapped[str] = mapped_column(
        String(20), default="weekly", nullable=False
    )
    decay_alert_threshold: Mapped[float] = mapped_column(
        Float, default=40.0, nullable=False
    )
    focus_categories: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    excluded_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="decay_preference"
    )

    def __repr__(self) -> str:
        return (
            f"<SkillDecayPreference "
            f"threshold={self.decay_alert_threshold}>"
        )
