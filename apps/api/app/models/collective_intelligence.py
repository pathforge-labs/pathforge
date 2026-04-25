"""
PathForge — Collective Intelligence Engine™ Models
===================================================
Domain models for the Collective Intelligence Engine — the industry's
first individual-facing system that provides AI-powered career market
intelligence, salary benchmarking, peer cohort analysis, and industry
trend radar, all personalized to Career DNA.

Models:
    IndustrySnapshot                   — Industry health + hiring trends
    SalaryBenchmark                    — Personalized salary positioning
    PeerCohortAnalysis                 — Anonymous peer comparison
    CareerPulseEntry                   — Composite career market health
    CollectiveIntelligencePreference   — User configuration

Enums:
    TrendDirection      — rising | stable | declining | emerging
    DemandIntensity     — low | moderate | high | very_high | critical
    PulseCategory       — critical | low | moderate | healthy | thriving
    BenchmarkCurrency   — EUR | USD | GBP | CHF | CAD | AUD | other

Proprietary Innovations:
    🔥 Career Pulse Index™          — Composite career market health score
    🔥 Peer Cohort Benchmarking™    — Anonymous comparison with similar pros
    🔥 Industry Trend Radar™        — AI-driven personalized trend analysis
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


class TrendDirection(enum.StrEnum):
    """Industry or career market trend direction."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    EMERGING = "emerging"


class DemandIntensity(enum.StrEnum):
    """Market demand intensity classification."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class PulseCategory(enum.StrEnum):
    """Career Pulse health classification (0-100 scale)."""

    CRITICAL = "critical"       # 0-20
    LOW = "low"                 # 21-40
    MODERATE = "moderate"       # 41-60
    HEALTHY = "healthy"         # 61-80
    THRIVING = "thriving"       # 81-100


class BenchmarkCurrency(enum.StrEnum):
    """Supported currencies for salary benchmarking."""

    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    OTHER = "other"


# ── IndustrySnapshot ──────────────────────────────────────────


class IndustrySnapshot(Base, UUIDMixin, TimestampMixin):
    """Collective Intelligence Engine™ — industry health snapshot.

    Industry Trend Radar™ — captures the current state of an industry
    relevant to the user's Career DNA, including hiring trends,
    emerging skills, salary ranges, and growth projections.

    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "ci_industry_snapshots"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_ci_industry_confidence_cap",
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
    industry: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
    )
    region: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    trend_direction: Mapped[str] = mapped_column(
        String(20), default=TrendDirection.STABLE.value,
        server_default="stable", nullable=False,
    )
    demand_intensity: Mapped[str] = mapped_column(
        String(20), default=DemandIntensity.MODERATE.value,
        server_default="moderate", nullable=False,
    )

    # ── Intelligence fields ──
    top_emerging_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    declining_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    avg_salary_range_min: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    avg_salary_range_max: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10), default=BenchmarkCurrency.EUR.value,
        server_default="EUR", nullable=False,
    )
    growth_rate_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    hiring_volume_trend: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    key_insights: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed industry trends from public market data",
        server_default="AI-analyzed industry trends from public market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Industry trends are AI-generated estimates based on publicly "
            "available data. Actual market conditions may vary by region "
            "and time. Maximum confidence: 85%."
        ),
        server_default=(
            "Industry trends are AI-generated estimates based on publicly "
            "available data. Actual market conditions may vary by region "
            "and time. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="industry_snapshots",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<IndustrySnapshot(industry={self.industry}, "
            f"trend={self.trend_direction}, demand={self.demand_intensity})>"
        )


# ── SalaryBenchmark ───────────────────────────────────────────


class SalaryBenchmark(Base, UUIDMixin, TimestampMixin):
    """Collective Intelligence Engine™ — personalized salary intelligence.

    Provides market-contextualized salary benchmarking using the user's
    Career DNA: role, skills, experience, and location. Outputs include
    percentile positioning, skill premiums, and negotiation data points.

    Confidence capped at 0.85 per PathForge transparency standards.
    """

    __tablename__ = "ci_salary_benchmarks"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_ci_salary_confidence_cap",
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
    role: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
    )
    experience_years: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )

    # ── Benchmark data ──
    benchmark_min: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    benchmark_median: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    benchmark_max: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    currency: Mapped[str] = mapped_column(
        String(10), default=BenchmarkCurrency.EUR.value,
        server_default="EUR", nullable=False,
    )
    user_percentile: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    skill_premium_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    experience_factor: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    negotiation_insights: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    premium_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed salary benchmarks from public market data",
        server_default="AI-analyzed salary benchmarks from public market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Salary benchmarks are AI-generated estimates. Actual "
            "compensation varies by company, negotiation, and benefits. "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "Salary benchmarks are AI-generated estimates. Actual "
            "compensation varies by company, negotiation, and benefits. "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="ci_salary_benchmarks",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<SalaryBenchmark(role={self.role}, location={self.location}, "
            f"median={self.benchmark_median})>"
        )


# ── PeerCohortAnalysis ────────────────────────────────────────


class PeerCohortAnalysis(Base, UUIDMixin, TimestampMixin):
    """Collective Intelligence Engine™ — Peer Cohort Benchmarking™.

    Provides anonymized comparison against professionals with similar
    Career DNA profiles. Uses k-anonymity (minimum 10 in cohort) to
    protect individual privacy while delivering actionable insights
    on relative positioning.

    Enterprise-only feature elsewhere — PathForge democratizes it.
    """

    __tablename__ = "ci_peer_cohort_analyses"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_ci_peer_cohort_confidence_cap",
        ),
        CheckConstraint(
            "cohort_size >= 10",
            name="ck_ci_peer_cohort_k_anonymity",
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

    # ── Cohort definition ──
    cohort_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False,
    )
    cohort_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10,
    )

    # ── Benchmarking results ──
    user_rank_percentile: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0,
    )
    avg_skills_count: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    user_skills_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    avg_experience_years: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    common_transitions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    top_differentiating_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    skill_gaps_vs_cohort: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-synthesized peer cohort from anonymized market data",
        server_default="AI-synthesized peer cohort from anonymized market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Peer cohort is AI-synthesized from general market data with "
            "k-anonymity (min 10 in cohort). No individual user data is "
            "shared. Maximum confidence: 85%."
        ),
        server_default=(
            "Peer cohort is AI-synthesized from general market data with "
            "k-anonymity (min 10 in cohort). No individual user data is "
            "shared. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="peer_cohort_analyses",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<PeerCohortAnalysis(cohort_size={self.cohort_size}, "
            f"rank={self.user_rank_percentile}%)>"
        )


# ── CareerPulseEntry ──────────────────────────────────────────


class CareerPulseEntry(Base, UUIDMixin, TimestampMixin):
    """Collective Intelligence Engine™ — Career Pulse Index™.

    The Career Pulse Index is a composite score (0-100) reflecting
    the real-time health of the user's career market segment.

    Components:
        - Demand: how much the market wants the user's skill set
        - Salary: how well-compensated the user's profile is
        - Skill relevance: how future-proof the user's skills are
        - Trend: overall industry trajectory

    No competitor offers a single composite career market health
    metric personalized to individual skills.
    """

    __tablename__ = "ci_career_pulse_entries"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_ci_pulse_confidence_cap",
        ),
        CheckConstraint(
            "pulse_score >= 0.0 AND pulse_score <= 100.0",
            name="ck_ci_pulse_score_range",
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

    # ── Pulse score ──
    pulse_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0,
    )
    pulse_category: Mapped[str] = mapped_column(
        String(20), default=PulseCategory.MODERATE.value,
        server_default="moderate", nullable=False,
    )
    trend_direction: Mapped[str] = mapped_column(
        String(20), default=TrendDirection.STABLE.value,
        server_default="stable", nullable=False,
    )

    # ── Component scores ──
    demand_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    salary_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    skill_relevance_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    trend_component: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Actionable intelligence ──
    top_opportunities: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    risk_factors: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    recommended_actions: Mapped[dict[str, Any] | None] = mapped_column(
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
        default="AI-computed Career Pulse Index from market intelligence",
        server_default="AI-computed Career Pulse Index from market intelligence",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Career Pulse Index is an AI-generated composite score. "
            "It reflects general market trends, not guaranteed outcomes. "
            "Use alongside your own research. Maximum confidence: 85%."
        ),
        server_default=(
            "Career Pulse Index is an AI-generated composite score. "
            "It reflects general market trends, not guaranteed outcomes. "
            "Use alongside your own research. Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="career_pulse_entries",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CareerPulseEntry(score={self.pulse_score}, "
            f"category={self.pulse_category}, trend={self.trend_direction})>"
        )


# ── CollectiveIntelligencePreference ──────────────────────────


class CollectiveIntelligencePreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Collective Intelligence Engine™.

    Supports user autonomy (PathForge Manifesto #5):
    users control which intelligence modules to include,
    preferred industries, and target locations for analysis.
    """

    __tablename__ = "ci_preferences"

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
    include_industry_pulse: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_salary_benchmarks: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_peer_analysis: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    preferred_industries: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    preferred_locations: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    preferred_currency: Mapped[str] = mapped_column(
        String(10), default=BenchmarkCurrency.EUR.value,
        server_default="EUR", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="ci_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<CollectiveIntelligencePreference(user_id={self.user_id}, "
            f"currency={self.preferred_currency})>"
        )
