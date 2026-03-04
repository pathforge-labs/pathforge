"""
PathForge — Career Simulation Engine™ Models
===============================================
Domain models for the Career Simulation Engine — the industry's
first consumer-grade "what-if" career planning tool.

Models:
    CareerSimulation     — Hub entity for one what-if scenario
    SimulationInput      — User-provided scenario parameters
    SimulationOutcome    — Projected results per dimension
    SimulationRecommendation — Actionable next steps
    SimulationPreference — User autonomy preferences

Enums:
    ScenarioType           — role_transition | geo_move | skill_investment | industry_pivot | seniority_jump
    SimulationStatus       — draft | running | completed | failed
    RecommendationPriority — critical | high | medium | nice_to_have

Proprietary Innovations:
    🔥 Career Scenario Simulator™     — Multi-variable what-if engine
    🔥 Scenario Confidence Metric™    — Composite score (0.85 hard cap)
    🔥 ROI Calculator™                — Per-scenario return-on-investment
    🔥 Scenario Comparison Matrix™    — Side-by-side up to 5 scenarios
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class ScenarioType(enum.StrEnum):
    """Classification for career simulation scenario types."""

    ROLE_TRANSITION = "role_transition"
    GEO_MOVE = "geo_move"
    SKILL_INVESTMENT = "skill_investment"
    INDUSTRY_PIVOT = "industry_pivot"
    SENIORITY_JUMP = "seniority_jump"


class SimulationStatus(enum.StrEnum):
    """Lifecycle status of a career simulation."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationPriority(enum.StrEnum):
    """Priority classification for simulation recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    NICE_TO_HAVE = "nice_to_have"


# ── CareerSimulation ──────────────────────────────────────────


class CareerSimulation(Base, UUIDMixin, TimestampMixin):
    """Career Scenario Simulator™ — "what-if" scenario result.

    Hub entity: one record per user scenario. Each simulation
    combines Career DNA context with LLM-powered projections
    to answer questions like:
        "What if I switch from Backend to ML Engineer?"
        "What if I move from Amsterdam to Berlin?"
        "What if I learn Kubernetes?"

    Confidence is hard-capped at 0.85 (MAX_SIMULATION_CONFIDENCE).
    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "career_simulations"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_simulation_confidence_cap",
        ),
    )

    # ── Foreign keys ──
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    scenario_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SimulationStatus.COMPLETED.value,
        server_default="completed", nullable=False, index=True,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    feasibility_rating: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    roi_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )

    # ── Projections ──
    salary_impact_percent: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    estimated_months: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )

    # ── Context ──
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-generated projection based on Career DNA and market data",
        server_default="AI-generated projection based on Career DNA and market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This simulation is an AI-generated projection, not a guarantee. "
            "Actual outcomes depend on market conditions, personal effort, "
            "and factors beyond prediction. Maximum confidence: 85%."
        ),
        server_default=(
            "This simulation is an AI-generated projection, not a guarantee. "
            "Actual outcomes depend on market conditions, personal effort, "
            "and factors beyond prediction. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Computed timestamp ──
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default="now()",
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="simulations",
    )
    inputs: Mapped[list[SimulationInput]] = relationship(
        "SimulationInput",
        back_populates="simulation",
        cascade="all, delete-orphan",
    )
    outcomes: Mapped[list[SimulationOutcome]] = relationship(
        "SimulationOutcome",
        back_populates="simulation",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list[SimulationRecommendation]] = relationship(
        "SimulationRecommendation",
        back_populates="simulation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CareerSimulation(id={self.id}, type={self.scenario_type}, "
            f"confidence={self.confidence_score})>"
        )


# ── SimulationInput ───────────────────────────────────────────


class SimulationInput(Base, UUIDMixin, TimestampMixin):
    """User-provided scenario parameters.

    Stores the key-value pairs that define each simulation
    scenario. For example, a role transition stores:
        parameter_name="target_role", parameter_value="ML Engineer"
        parameter_name="target_industry", parameter_value="AI/ML"
    """

    __tablename__ = "simulation_inputs"

    simulation_id: Mapped[str] = mapped_column(
        ForeignKey("career_simulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    parameter_value: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    parameter_type: Mapped[str] = mapped_column(
        String(30), default="string", server_default="string", nullable=False,
    )

    # ── Relationships ──
    simulation: Mapped[CareerSimulation] = relationship(
        "CareerSimulation", back_populates="inputs",
    )

    def __repr__(self) -> str:
        return (
            f"<SimulationInput(name={self.parameter_name}, "
            f"value={self.parameter_value})>"
        )


# ── SimulationOutcome ────────────────────────────────────────


class SimulationOutcome(Base, UUIDMixin, TimestampMixin):
    """Projected results per dimension.

    Each what-if scenario produces multiple dimensional projections:
    salary, market demand, growth potential, automation risk, etc.

    Stores current_value → projected_value → delta for each dimension.
    """

    __tablename__ = "simulation_outcomes"

    simulation_id: Mapped[str] = mapped_column(
        ForeignKey("career_simulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    current_value: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    projected_value: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    delta: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    unit: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ──
    simulation: Mapped[CareerSimulation] = relationship(
        "CareerSimulation", back_populates="outcomes",
    )

    def __repr__(self) -> str:
        return (
            f"<SimulationOutcome(dim={self.dimension}, "
            f"delta={self.delta})>"
        )


# ── SimulationRecommendation ────────────────────────────────


class SimulationRecommendation(Base, UUIDMixin, TimestampMixin):
    """Actionable next steps from simulation.

    Each simulation generates prioritized recommendations
    with time estimates and detailed descriptions.
    """

    __tablename__ = "simulation_recommendations"

    simulation_id: Mapped[str] = mapped_column(
        ForeignKey("career_simulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20), default=RecommendationPriority.MEDIUM.value,
        server_default="medium", nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    estimated_weeks: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )

    # ── Relationships ──
    simulation: Mapped[CareerSimulation] = relationship(
        "CareerSimulation", back_populates="recommendations",
    )

    def __repr__(self) -> str:
        return (
            f"<SimulationRecommendation(title={self.title}, "
            f"priority={self.priority})>"
        )


# ── SimulationPreference ────────────────────────────────────


class SimulationPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Career Simulation Engine™.

    Supports user autonomy (PathForge Manifesto #5):
    users control default scenario types, maximum saved
    simulations, and notification preferences.
    """

    __tablename__ = "simulation_preferences"

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
    default_scenario_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )
    max_scenarios: Mapped[int] = mapped_column(
        Integer, default=50, server_default="50", nullable=False,
    )
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="simulation_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<SimulationPreference(user_id={self.user_id}, "
            f"max_scenarios={self.max_scenarios})>"
        )
