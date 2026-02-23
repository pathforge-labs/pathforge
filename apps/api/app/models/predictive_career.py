"""
PathForge — Predictive Career Engine™ Models
=============================================
Domain models for the Predictive Career Engine — the industry's first
individual-facing predictive intelligence system that detects emerging
roles, forecasts industry disruptions, surfaces proactive opportunities,
and computes a composite forward-looking career outlook score, all
personalized to Career DNA.

Models:
    EmergingRole                — Detected emerging role opportunities
    DisruptionForecast          — Industry/tech disruption predictions
    OpportunitySurface          — Proactively detected opportunities
    CareerForecast              — Composite predictive career outlook
    PredictiveCareerPreference  — User preferences for predictions

Enums:
    EmergenceStage   — nascent | growing | mainstream | declining
    DisruptionType   — technology | regulation | market_shift | automation | consolidation
    OpportunityType  — emerging_role | skill_demand | industry_growth | geographic_expansion
    RiskTolerance    — conservative | moderate | aggressive

Proprietary Innovations:
    🔥 Emerging Role Radar™           — AI detects nascent roles before job boards
    🔥 Disruption Forecast Engine™    — Personalized disruption predictions
    🔥 Career Forecast Index™         — Composite forward-looking career score
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class EmergenceStage(enum.StrEnum):
    """Stage in the role emergence lifecycle."""

    NASCENT = "nascent"        # Early signals, <5% of market
    GROWING = "growing"        # Accelerating demand, 5-25%
    MAINSTREAM = "mainstream"  # Established demand, >25%
    DECLINING = "declining"    # Past peak, shrinking demand


class DisruptionType(enum.StrEnum):
    """Category of career-impacting disruption."""

    TECHNOLOGY = "technology"
    REGULATION = "regulation"
    MARKET_SHIFT = "market_shift"
    AUTOMATION = "automation"
    CONSOLIDATION = "consolidation"


class OpportunityType(enum.StrEnum):
    """Category of proactively surfaced opportunity."""

    EMERGING_ROLE = "emerging_role"
    SKILL_DEMAND = "skill_demand"
    INDUSTRY_GROWTH = "industry_growth"
    GEOGRAPHIC_EXPANSION = "geographic_expansion"


class RiskTolerance(enum.StrEnum):
    """User risk appetite for predictive recommendations."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ForecastOutlook(enum.StrEnum):
    """Career forecast outlook classification (0-100 scale)."""

    CRITICAL = "critical"       # 0-20
    AT_RISK = "at_risk"         # 21-40
    MODERATE = "moderate"       # 41-60
    FAVORABLE = "favorable"     # 61-80
    EXCEPTIONAL = "exceptional" # 81-100


# ── EmergingRole ──────────────────────────────────────────────


class EmergingRole(Base, UUIDMixin, TimestampMixin):
    """Predictive Career Engine™ — Emerging Role Radar™.

    Detects nascent and growing roles that match the user's
    existing skill set, before they appear on mainstream job boards.
    Includes skill overlap scoring and time-to-mainstream estimates.

    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "pc_emerging_roles"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_pc_emerging_role_confidence_cap",
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
    role_title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    industry: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
    )
    emergence_stage: Mapped[str] = mapped_column(
        String(20), default=EmergenceStage.NASCENT.value,
        server_default="nascent", nullable=False, index=True,
    )

    # ── Intelligence fields ──
    growth_rate_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    skill_overlap_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    time_to_mainstream_months: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    required_new_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    transferable_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    avg_salary_range_min: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    avg_salary_range_max: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    key_employers: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed emerging role signals from public market data",
        server_default="AI-analyzed emerging role signals from public market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Emerging role predictions are AI-generated estimates based "
            "on market trends. Actual role emergence timelines may vary. "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "Emerging role predictions are AI-generated estimates based "
            "on market trends. Actual role emergence timelines may vary. "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="emerging_roles",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<EmergingRole(title={self.role_title}, "
            f"stage={self.emergence_stage}, overlap={self.skill_overlap_pct}%)>"
        )


# ── DisruptionForecast ────────────────────────────────────────


class DisruptionForecast(Base, UUIDMixin, TimestampMixin):
    """Predictive Career Engine™ — Disruption Forecast Engine™.

    Predicts industry and technology disruptions that may impact
    the user's career trajectory. Includes severity scoring,
    timeline estimates, and personalized impact assessment.

    Confidence capped at 0.85 per PathForge transparency standards.
    """

    __tablename__ = "pc_disruption_forecasts"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_pc_disruption_confidence_cap",
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
    disruption_title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    disruption_type: Mapped[str] = mapped_column(
        String(30), default=DisruptionType.TECHNOLOGY.value,
        server_default="technology", nullable=False, index=True,
    )
    industry: Mapped[str] = mapped_column(
        String(200), nullable=False,
    )

    # ── Intelligence fields ──
    severity_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0,
    )
    timeline_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12,
    )
    impact_on_user: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    affected_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    mitigation_strategies: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    opportunity_from_disruption: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed disruption signals from industry trend data",
        server_default="AI-analyzed disruption signals from industry trend data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Disruption forecasts are AI-generated predictions based on "
            "industry trends. Actual disruption timing and impact may "
            "differ. Maximum confidence: 85%."
        ),
        server_default=(
            "Disruption forecasts are AI-generated predictions based on "
            "industry trends. Actual disruption timing and impact may "
            "differ. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="disruption_forecasts",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<DisruptionForecast(title={self.disruption_title}, "
            f"type={self.disruption_type}, severity={self.severity_score})>"
        )


# ── OpportunitySurface ────────────────────────────────────────


class OpportunitySurface(Base, UUIDMixin, TimestampMixin):
    """Predictive Career Engine™ — Proactive Opportunity Surfacing.

    Identifies career opportunities before they become obvious,
    by combining skill adjacency, market signals, and Career DNA
    context. Each opportunity includes relevance scoring and
    concrete action items.

    Enterprise-only elsewhere — PathForge democratizes it.
    """

    __tablename__ = "pc_opportunity_surfaces"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_pc_opportunity_confidence_cap",
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
    opportunity_title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    opportunity_type: Mapped[str] = mapped_column(
        String(30), default=OpportunityType.EMERGING_ROLE.value,
        server_default="emerging_role", nullable=False, index=True,
    )
    source_signal: Mapped[str] = mapped_column(
        String(200), nullable=False,
        default="market_analysis",
        server_default="market_analysis",
    )

    # ── Intelligence fields ──
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    action_items: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    required_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    skill_gap_analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    time_sensitivity: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-surfaced opportunity from market and skill signals",
        server_default="AI-surfaced opportunity from market and skill signals",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Opportunities are AI-identified based on market signals "
            "and skill matching. Verify opportunities independently "
            "before acting. Maximum confidence: 85%."
        ),
        server_default=(
            "Opportunities are AI-identified based on market signals "
            "and skill matching. Verify opportunities independently "
            "before acting. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="opportunity_surfaces",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<OpportunitySurface(title={self.opportunity_title}, "
            f"type={self.opportunity_type}, relevance={self.relevance_score})>"
        )


# ── CareerForecast ────────────────────────────────────────────


class CareerForecast(Base, UUIDMixin, TimestampMixin):
    """Predictive Career Engine™ — Career Forecast Index™.

    Composite forward-looking career outlook score (0-100)
    combining role emergence, disruption risk, opportunity
    potential, and market trend signals into a single actionable
    metric.

    Components:
        - Role: emerging role opportunity strength
        - Disruption: inverse disruption severity
        - Opportunity: proactive opportunity potential
        - Trend: overall market trajectory

    No competitor offers a single composite forward-looking
    career score personalized to individual skills.
    """

    __tablename__ = "pc_career_forecasts"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_pc_forecast_confidence_cap",
        ),
        CheckConstraint(
            "outlook_score >= 0.0 AND outlook_score <= 100.0",
            name="ck_pc_forecast_outlook_range",
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

    # ── Forecast score ──
    outlook_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0,
    )
    outlook_category: Mapped[str] = mapped_column(
        String(20), default=ForecastOutlook.MODERATE.value,
        server_default="moderate", nullable=False,
    )
    forecast_horizon_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12,
    )

    # ── Component scores ──
    role_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    disruption_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    opportunity_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    trend_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Actionable intelligence ──
    top_actions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    key_risks: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    key_opportunities: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-computed Career Forecast Index from predictive signals",
        server_default="AI-computed Career Forecast Index from predictive signals",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Career Forecast Index is an AI-generated composite score. "
            "It reflects predicted market trends, not guaranteed outcomes. "
            "Use alongside your own research. Maximum confidence: 85%."
        ),
        server_default=(
            "Career Forecast Index is an AI-generated composite score. "
            "It reflects predicted market trends, not guaranteed outcomes. "
            "Use alongside your own research. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="career_forecasts",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CareerForecast(outlook={self.outlook_score}, "
            f"category={self.outlook_category}, "
            f"horizon={self.forecast_horizon_months}mo)>"
        )


# ── PredictiveCareerPreference ────────────────────────────────


class PredictiveCareerPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Predictive Career Engine™.

    Supports user autonomy (PathForge Manifesto #5):
    users control forecast horizon, which prediction modules
    to include, risk tolerance, and focus industries.
    """

    __tablename__ = "pc_preferences"

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
    forecast_horizon_months: Mapped[int] = mapped_column(
        Integer, default=12, server_default="12", nullable=False,
    )
    include_emerging_roles: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_disruption_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_opportunities: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    risk_tolerance: Mapped[str] = mapped_column(
        String(20), default=RiskTolerance.MODERATE.value,
        server_default="moderate", nullable=False,
    )
    focus_industries: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    focus_regions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="predictive_career_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<PredictiveCareerPreference(user_id={self.user_id}, "
            f"horizon={self.forecast_horizon_months}mo, "
            f"risk={self.risk_tolerance})>"
        )
