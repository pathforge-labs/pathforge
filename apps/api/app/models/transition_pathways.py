"""
PathForge — Transition Pathways Models
=========================================
Domain models for the Transition Pathways module — the industry's
first consumer-grade career transition intelligence system.

Models:
    1. TransitionPath — Core pathway: from_role → to_role with confidence
    2. SkillBridgeEntry — Per-skill gap analysis for a transition
    3. TransitionMilestone — Phased action plan checkpoint
    4. TransitionComparison — Source vs target role dimension comparison
    5. TransitionPreference — User autonomy controls for transitions

Proprietary Innovations:
    - Transition Confidence Score™ (personalized success probability)
    - Skill Bridge Matrix™ (exact skills to acquire with time estimates)
    - Career Velocity Corridor™ (realistic transition timeline ranges)
    - Transition Timeline Engine™ (milestone-based action plans)
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


class TransitionDifficulty(enum.StrEnum):
    """Difficulty classification for a career transition."""

    EASY = "easy"
    MODERATE = "moderate"
    CHALLENGING = "challenging"
    EXTREME = "extreme"


class TransitionStatus(enum.StrEnum):
    """Lifecycle status of a saved transition path."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MilestonePhase(enum.StrEnum):
    """Phase classification for transition milestones."""

    PREPARATION = "preparation"
    SKILL_BUILDING = "skill_building"
    TRANSITION = "transition"
    ESTABLISHMENT = "establishment"


class SkillBridgePriority(enum.StrEnum):
    """Priority classification for skill gap entries."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    NICE_TO_HAVE = "nice_to_have"


# ── TransitionPath ─────────────────────────────────────────────


class TransitionPath(UUIDMixin, TimestampMixin, Base):
    """Transition Confidence Score™ — evidence-based career pivot pathway.

    Core analysis model:
        TransitionConfidence = SkillOverlap(current, target)
                             × MarketDemandFactor(target_role_demand)
                             × SeniorityGapAdjustment(level_delta)
                             × LLMContextualScore(career_narrative)
                             ± ConfidenceInterval(data_quality)

    Each path produces a confidence score (0.0–0.85), difficulty
    classification, skill overlap percentage, and estimated timeline
    with transparent factor breakdown for explainability.

    Confidence is hard-capped at 0.85 because LLM-only estimates
    should never claim near-certainty for career outcomes.
    """

    __tablename__ = "transition_paths"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source and target roles
    from_role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    to_role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Transition intelligence
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        default=TransitionDifficulty.MODERATE.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=TransitionStatus.ACTIVE.value,
        nullable=False,
    )

    # Skill analysis
    skill_overlap_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    skills_to_acquire_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Timeline estimation (Career Velocity Corridor™)
    estimated_duration_months: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    optimistic_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realistic_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conservative_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Impact analysis
    salary_impact_percent: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    success_probability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # LLM reasoning and factors
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Data transparency
    data_source: Mapped[str] = mapped_column(
        String(100),
        default="ai_analysis",
        server_default="ai_analysis",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="AI-generated estimate based on career profile analysis. "
        "Actual outcomes may vary based on individual circumstances.",
        nullable=False,
    )

    # Computation timestamp
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="transition_paths"
    )
    skill_bridge_entries: Mapped[list[SkillBridgeEntry]] = relationship(
        "SkillBridgeEntry",
        back_populates="transition_path",
        cascade="all, delete-orphan",
    )
    milestones: Mapped[list[TransitionMilestone]] = relationship(
        "TransitionMilestone",
        back_populates="transition_path",
        cascade="all, delete-orphan",
    )
    comparisons: Mapped[list[TransitionComparison]] = relationship(
        "TransitionComparison",
        back_populates="transition_path",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<TransitionPath {self.from_role} → {self.to_role} "
            f"confidence={self.confidence_score:.2f}>"
        )


# ── SkillBridgeEntry ───────────────────────────────────────────


class SkillBridgeEntry(UUIDMixin, TimestampMixin, Base):
    """Skill Bridge Matrix™ — per-skill gap analysis for a transition.

    Identifies each skill required by the target role, whether the
    user already holds it, and if not, how to acquire it with
    estimated time investment and priority ranking.
    """

    __tablename__ = "skill_bridge_entries"

    transition_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transition_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), default="technical", nullable=False
    )
    is_already_held: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    current_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Acquisition guidance
    acquisition_method: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    estimated_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_resources: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Priority scoring
    priority: Mapped[str] = mapped_column(
        String(50),
        default=SkillBridgePriority.MEDIUM.value,
        nullable=False,
    )
    impact_on_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Relationships
    transition_path: Mapped[TransitionPath] = relationship(
        "TransitionPath", back_populates="skill_bridge_entries"
    )

    def __repr__(self) -> str:
        held_flag = "✓" if self.is_already_held else "✗"
        return f"<SkillBridgeEntry {self.skill_name} [{held_flag}] {self.priority}>"


# ── TransitionMilestone ────────────────────────────────────────


class TransitionMilestone(UUIDMixin, TimestampMixin, Base):
    """Transition Timeline Engine™ — phased action plan checkpoint.

    Breaks the transition into concrete, time-boxed milestones
    across 4 phases: preparation → skill_building → transition →
    establishment. Week targets are relative to transition start.
    """

    __tablename__ = "transition_milestones"

    transition_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transition_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    phase: Mapped[str] = mapped_column(
        String(50),
        default=MilestonePhase.PREPARATION.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    transition_path: Mapped[TransitionPath] = relationship(
        "TransitionPath", back_populates="milestones"
    )

    def __repr__(self) -> str:
        status = "✓" if self.is_completed else "○"
        return f"<TransitionMilestone [{status}] W{self.target_week}: {self.title}>"


# ── TransitionComparison ───────────────────────────────────────


class TransitionComparison(UUIDMixin, TimestampMixin, Base):
    """Role comparison dimension — source vs target role comparison.

    Compares current and target roles across multiple dimensions
    (salary, market demand, growth potential, automation risk)
    with delta values and contextual reasoning.
    """

    __tablename__ = "transition_comparisons"

    transition_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transition_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    source_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    transition_path: Mapped[TransitionPath] = relationship(
        "TransitionPath", back_populates="comparisons"
    )

    def __repr__(self) -> str:
        return (
            f"<TransitionComparison {self.dimension} "
            f"delta={self.delta:+.1f}>"
        )


# ── TransitionPreference ───────────────────────────────────────


class TransitionPreference(UUIDMixin, TimestampMixin, Base):
    """User preferences for Transition Pathways module.

    Supports user autonomy (PathForge Manifesto #5):
    users control which industries to explore, which roles to
    exclude, minimum confidence thresholds, and maximum timeline
    preferences.
    """

    __tablename__ = "transition_preferences"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Exploration preferences
    preferred_industries: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    excluded_roles: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )

    # Filtering thresholds
    min_confidence: Mapped[float] = mapped_column(
        Float, default=0.3, server_default="0.3", nullable=False
    )
    max_timeline_months: Mapped[int] = mapped_column(
        Integer, default=36, server_default="36", nullable=False
    )

    # Notifications
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="transition_preference"
    )

    def __repr__(self) -> str:
        return (
            f"<TransitionPreference min_conf={self.min_confidence} "
            f"max_months={self.max_timeline_months}>"
        )
