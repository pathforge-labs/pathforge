"""
PathForge — Career Action Planner™ Models
============================================
Domain models for Phase D: Career Execution Intelligence.

The Career Action Planner™ is the industry's first consumer-facing platform
that bridges career intelligence with structured, AI-driven career execution
planning using sprint methodology.

Models:
    CareerActionPlan              — Hub model: the user's career action plan
    PlanMilestone                 — Individual milestone within a plan
    MilestoneProgress             — Progress tracking entries per milestone
    PlanRecommendation            — AI recommendations from intelligence engines
    CareerActionPlannerPreference — User configuration for plan generation

Enums:
    PlanType           — skill_development | role_transition | salary_growth | threat_mitigation | opportunity_capture
    PlanStatus         — draft | active | paused | completed | archived
    MilestoneCategory  — learning | certification | networking | project | application | interview_prep
    MilestoneStatus    — not_started | in_progress | completed | skipped | blocked
    SourceEngine       — threat_radar | skill_decay | salary_intelligence | transition_pathways | ...

Proprietary Innovations:
    🔥 Career Sprint Methodology™         — Time-boxed career development cycles
    🔥 Intelligence-to-Action Bridge™     — Converts intelligence into ranked actions
    🔥 Adaptive Plan Recalculation™       — Dynamic re-prioritization on career events
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.career_dna import CareerDNA
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class PlanType(enum.StrEnum):
    """Career action plan type classification."""

    SKILL_DEVELOPMENT = "skill_development"
    ROLE_TRANSITION = "role_transition"
    SALARY_GROWTH = "salary_growth"
    THREAT_MITIGATION = "threat_mitigation"
    OPPORTUNITY_CAPTURE = "opportunity_capture"


class PlanStatus(enum.StrEnum):
    """Lifecycle status of a career action plan."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MilestoneCategory(enum.StrEnum):
    """Category classification for plan milestones."""

    LEARNING = "learning"
    CERTIFICATION = "certification"
    NETWORKING = "networking"
    PROJECT = "project"
    APPLICATION = "application"
    INTERVIEW_PREP = "interview_prep"


class MilestoneStatus(enum.StrEnum):
    """Lifecycle status of a plan milestone."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class SourceEngine(enum.StrEnum):
    """Intelligence engine that generated a recommendation."""

    THREAT_RADAR = "threat_radar"
    SKILL_DECAY = "skill_decay"
    SALARY_INTELLIGENCE = "salary_intelligence"
    TRANSITION_PATHWAYS = "transition_pathways"
    CAREER_SIMULATION = "career_simulation"
    HIDDEN_JOB_MARKET = "hidden_job_market"
    PREDICTIVE_CAREER = "predictive_career"
    COLLECTIVE_INTELLIGENCE = "collective_intelligence"


# ── CareerActionPlan ───────────────────────────────────────────


class CareerActionPlan(Base, UUIDMixin, TimestampMixin):
    """Career Action Planner™ — hub model for career action plans.

    Career Sprint Methodology™ — structures career development into
    time-boxed 2-4 week sprints with measurable milestones. Each plan
    includes:
        - Title and objective describing the career goal
        - Plan type (skill dev, role transition, salary growth, etc.)
        - Priority score ranked by urgency and impact
        - Confidence score (hard-capped at 0.85)

    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "career_action_plans"
    __table_args__ = (
        CheckConstraint(
            "confidence <= 0.85",
            name="ck_career_action_plan_confidence_cap",
        ),
        CheckConstraint(
            "priority_score >= 0.0 AND priority_score <= 100.0",
            name="ck_career_action_plan_priority_range",
        ),
    )

    # ── Foreign keys ──
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    title: Mapped[str] = mapped_column(
        String(300), nullable=False,
    )
    objective: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    plan_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=PlanStatus.DRAFT.value,
        server_default="draft",
        nullable=False,
        index=True,
    )

    # ── Intelligence scores ──
    priority_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(300),
        default="AI-powered career action planning via Career Sprint Methodology™",
        server_default=(
            "AI-powered career action planning via Career Sprint Methodology™"
        ),
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "AI-generated career action plan — milestones are suggestions, "
            "not guarantees. Timelines are estimates. Verify with professional "
            "career advisors when making major career decisions. "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "AI-generated career action plan — milestones are suggestions, "
            "not guarantees. Timelines are estimates. Verify with professional "
            "career advisors when making major career decisions. "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="career_action_plans",
    )
    user: Mapped[User] = relationship("User")
    milestones: Mapped[list[PlanMilestone]] = relationship(
        "PlanMilestone",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanMilestone.priority",
    )
    recommendations: Mapped[list[PlanRecommendation]] = relationship(
        "PlanRecommendation",
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CareerActionPlan(title={self.title!r}, "
            f"type={self.plan_type}, status={self.status})>"
        )


# ── PlanMilestone ──────────────────────────────────────────────


class PlanMilestone(Base, UUIDMixin, TimestampMixin):
    """Individual milestone within a Career Action Plan.

    Each milestone represents a concrete, actionable step in the user's
    career sprint — with a target date, category, effort estimate,
    and evidence requirements for completion.
    """

    __tablename__ = "plan_milestones"
    __table_args__ = (
        CheckConstraint(
            "priority >= 1 AND priority <= 10",
            name="ck_plan_milestone_priority_range",
        ),
        CheckConstraint(
            "effort_hours >= 0",
            name="ck_plan_milestone_effort_positive",
        ),
    )

    # ── Foreign keys ──
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("career_action_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    title: Mapped[str] = mapped_column(
        String(300), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    target_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=MilestoneStatus.NOT_STARTED.value,
        server_default="not_started",
        nullable=False,
        index=True,
    )
    effort_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
    )
    evidence_required: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ──
    plan: Mapped[CareerActionPlan] = relationship(
        "CareerActionPlan", back_populates="milestones",
    )
    progress_entries: Mapped[list[MilestoneProgress]] = relationship(
        "MilestoneProgress",
        back_populates="milestone",
        cascade="all, delete-orphan",
        order_by="MilestoneProgress.logged_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<PlanMilestone(title={self.title!r}, "
            f"category={self.category}, status={self.status})>"
        )


# ── MilestoneProgress ─────────────────────────────────────────


class MilestoneProgress(Base, UUIDMixin, TimestampMixin):
    """Progress tracking entry for a milestone.

    Users log progress against individual milestones — including
    percentage completion, notes, and evidence URLs.
    """

    __tablename__ = "milestone_progress"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0.0 AND progress_percent <= 100.0",
            name="ck_milestone_progress_percent_range",
        ),
    )

    # ── Foreign keys ──
    milestone_id: Mapped[str] = mapped_column(
        ForeignKey("plan_milestones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    progress_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    evidence_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
    )

    # ── Relationships ──
    milestone: Mapped[PlanMilestone] = relationship(
        "PlanMilestone", back_populates="progress_entries",
    )

    def __repr__(self) -> str:
        return (
            f"<MilestoneProgress(milestone_id={self.milestone_id}, "
            f"progress={self.progress_percent}%)>"
        )


# ── PlanRecommendation ─────────────────────────────────────────


class PlanRecommendation(Base, UUIDMixin, TimestampMixin):
    """AI-generated recommendation connected to intelligence engines.

    Intelligence-to-Action Bridge™ — each recommendation links back
    to a specific intelligence engine (Threat Radar, Skill Decay, etc.)
    and includes urgency, impact scoring, and rationale.
    """

    __tablename__ = "plan_recommendations"
    __table_args__ = (
        CheckConstraint(
            "impact_score >= 0.0 AND impact_score <= 100.0",
            name="ck_plan_recommendation_impact_range",
        ),
    )

    # ── Foreign keys ──
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("career_action_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    source_engine: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True,
    )
    recommendation_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(300), nullable=False,
    )
    rationale: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    urgency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
    )
    impact_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    linked_entity_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
    )

    # ── Detailed context (JSON) ──
    context_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Relationships ──
    plan: Mapped[CareerActionPlan] = relationship(
        "CareerActionPlan", back_populates="recommendations",
    )

    def __repr__(self) -> str:
        return (
            f"<PlanRecommendation(engine={self.source_engine}, "
            f"title={self.title!r}, urgency={self.urgency})>"
        )


# ── CareerActionPlannerPreference ──────────────────────────────


class CareerActionPlannerPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Career Action Planner™.

    Supports user autonomy (PathForge Manifesto #5):
    users control sprint length, maximum milestones, focus areas,
    and notification frequency for their career action plans.
    """

    __tablename__ = "career_action_planner_preferences"

    # ── Foreign keys ──
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Preference fields ──
    preferred_sprint_length_weeks: Mapped[int] = mapped_column(
        Integer, default=2, server_default="2", nullable=False,
    )
    max_milestones_per_plan: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5", nullable=False,
    )
    focus_areas: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    notification_frequency: Mapped[str] = mapped_column(
        String(20), default="weekly", server_default="weekly", nullable=False,
    )
    auto_generate_recommendations: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="career_action_planner_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<CareerActionPlannerPreference(user_id={self.user_id}, "
            f"sprint_length={self.preferred_sprint_length_weeks}w)>"
        )
