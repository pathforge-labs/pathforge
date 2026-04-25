"""
PathForge — Salary Intelligence Engine™ Models
==================================================
Domain models for the Salary Intelligence Engine — the industry's
first consumer-grade personalized salary intelligence system.

Models:
    1. SalaryEstimate — Personalized salary range calculation
    2. SkillSalaryImpact — Per-skill salary contribution analysis
    3. SalaryHistoryEntry — Point-in-time salary trajectory tracking
    4. SalaryScenario — What-if salary simulation results
    5. SalaryPreference — User salary tracking preferences

Proprietary Innovations:
    - Personalized Salary Range™ (multi-factor career DNA-driven estimation)
    - Skill Premium Mapping™ (per-skill salary impact quantification)
    - Salary Trajectory Engine™ (historical tracking with projections)
    - What-If Salary Simulator™ (scenario-based salary modeling)
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


class SeniorityLevel(enum.StrEnum):
    """Standardized seniority classification for salary modeling."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"


class ScenarioType(enum.StrEnum):
    """What-if salary scenario type classification."""

    ADD_SKILL = "add_skill"
    REMOVE_SKILL = "remove_skill"
    CHANGE_LOCATION = "change_location"
    CHANGE_SENIORITY = "change_seniority"
    CHANGE_INDUSTRY = "change_industry"
    ADD_CERTIFICATION = "add_certification"


class SalaryCurrency(enum.StrEnum):
    """Supported currencies for salary estimates."""

    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    CHF = "CHF"


# ── SalaryEstimate ─────────────────────────────────────────────


class SalaryEstimate(UUIDMixin, TimestampMixin, Base):
    """Personalized Salary Range™ — multi-factor salary estimation.

    Core calculation model:
        PersonalizedSalary = BaseSalary(role, location, seniority)
                           × SkillPremiumFactor(rare_skills, in_demand_skills)
                           × ExperienceMultiplier(years, relevance)
                           × MarketConditionAdjustment(supply_demand_ratio)
                           ± ConfidenceInterval(data_points, recency)

    Each estimate produces a min/median/max range with a confidence
    score and transparent factor breakdown for explainability.
    """

    __tablename__ = "salary_estimates"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=False)

    # Salary range
    estimated_min: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_max: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_median: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False
    )

    # Confidence & data quality
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    data_points_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    market_percentile: Mapped[float] = mapped_column(
        Float, nullable=True
    )

    # Factor breakdown (explainability)
    base_salary_factor: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    skill_premium_factor: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    experience_multiplier: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    market_condition_adjustment: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # LLM reasoning
    analysis_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    factors_detail: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Timestamp for when the estimate was computed
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="salary_estimates"
    )

    def __repr__(self) -> str:
        return (
            f"<SalaryEstimate {self.role_title} "
            f"{self.estimated_min}-{self.estimated_max} {self.currency}>"
        )


# ── SkillSalaryImpact ─────────────────────────────────────────


class SkillSalaryImpact(UUIDMixin, TimestampMixin, Base):
    """Skill Premium Mapping™ — per-skill salary contribution analysis.

    Quantifies how each skill in the user's Career DNA affects
    their market value. Combines:
        - Market demand premium (high-demand skills command higher salaries)
        - Scarcity factor (rare skill + high demand = maximum premium)
        - Cross-industry transferability bonus
    """

    __tablename__ = "skill_salary_impacts"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Impact quantification
    salary_impact_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    salary_impact_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    demand_premium: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    scarcity_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # Classification
    impact_direction: Mapped[str] = mapped_column(
        String(20), default="positive", server_default="positive", nullable=False
    )
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When this impact was last computed
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="skill_salary_impacts"
    )

    def __repr__(self) -> str:
        return (
            f"<SkillSalaryImpact {self.skill_name} "
            f"{self.salary_impact_percent:+.1f}%>"
        )


# ── SalaryHistoryEntry ─────────────────────────────────────────


class SalaryHistoryEntry(UUIDMixin, TimestampMixin, Base):
    """Salary Trajectory Engine™ — point-in-time salary tracking.

    Stores a snapshot of the user's salary estimate at a given
    moment, enabling historical trend analysis and trajectory
    projections. Auto-created each time a full scan completes.
    """

    __tablename__ = "salary_history_entries"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot values
    estimated_min: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_max: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_median: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    market_percentile: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Context at time of snapshot
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    skills_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Factor snapshot for comparison over time
    factors_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="salary_history"
    )

    def __repr__(self) -> str:
        return (
            f"<SalaryHistoryEntry {self.snapshot_date} "
            f"€{self.estimated_median:,.0f}>"
        )


# ── SalaryScenario ─────────────────────────────────────────────


class SalaryScenario(UUIDMixin, TimestampMixin, Base):
    """What-If Salary Simulator™ — scenario-based salary modeling.

    Allows users to explore salary impact of career decisions:
        - Adding/removing skills
        - Relocating to different cities/countries
        - Changing seniority level
        - Switching industries
        - Adding certifications
    """

    __tablename__ = "salary_scenarios"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scenario definition
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_label: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_input: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )

    # Projected outcome
    projected_min: Mapped[float] = mapped_column(Float, nullable=False)
    projected_max: Mapped[float] = mapped_column(Float, nullable=False)
    projected_median: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False
    )

    # Delta from current estimate
    delta_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    delta_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # LLM reasoning
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="salary_scenarios"
    )

    def __repr__(self) -> str:
        return (
            f"<SalaryScenario {self.scenario_type} "
            f"delta={self.delta_percent:+.1f}%>"
        )


# ── SalaryPreference ───────────────────────────────────────────


class SalaryPreference(UUIDMixin, TimestampMixin, Base):
    """User preferences for Salary Intelligence Engine tracking.

    Supports user autonomy (PathForge Manifesto #5):
    users control currency display, salary target tracking,
    notification preferences, and comparison markets.
    """

    __tablename__ = "salary_preferences"

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

    # Display preferences
    preferred_currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False
    )
    include_benefits: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Target tracking
    target_salary: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    target_currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False
    )

    # Notifications
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    notification_frequency: Mapped[str] = mapped_column(
        String(50), default="monthly", server_default="monthly", nullable=False
    )

    # Comparison scope
    comparison_market: Mapped[str] = mapped_column(
        String(100), default="Netherlands", server_default="Netherlands",
        nullable=False,
    )
    comparison_industries: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="salary_preference"
    )

    def __repr__(self) -> str:
        return (
            f"<SalaryPreference currency={self.preferred_currency} "
            f"target={self.target_salary}>"
        )
