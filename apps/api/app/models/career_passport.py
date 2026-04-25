"""
PathForge — Cross-Border Career Passport™ Models
===================================================
Domain models for the Cross-Border Career Passport — the industry's
first system that provides AI-powered credential mapping, visa feasibility
assessment, cost-of-living comparison, and multi-country market demand
analysis, all personalized to Career DNA.

Models:
    CredentialMapping            — Qualification → international EQF equivalent
    CountryComparison            — Side-by-side country mobility analysis
    VisaAssessment               — Visa/permit feasibility assessment
    MarketDemandEntry            — Role demand snapshot by country
    CareerPassportPreference     — User configuration

Enums:
    EQFLevel           — level_1 through level_8 (EU Bologna)
    DemandLevel        — low | moderate | high | very_high
    VisaCategory       — free_movement | work_permit | blue_card | skilled_worker | investor | other
    ComparisonStatus   — draft | active | archived

Proprietary Innovations:
    🔥 Career Passport Score™         — Composite mobility readiness metric
    🔥 EQF Intelligence Engine™       — AI-powered qualification mapping
    🔥 Purchasing Power Calculator™   — Personalized financial impact analysis
    🔥 Visa Eligibility Predictor™    — AI-assessed visa feasibility
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


class EQFLevel(enum.StrEnum):
    """European Qualifications Framework level (1-8, Bologna-aligned)."""

    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"
    LEVEL_5 = "level_5"
    LEVEL_6 = "level_6"
    LEVEL_7 = "level_7"
    LEVEL_8 = "level_8"


class DemandLevel(enum.StrEnum):
    """Market demand intensity classification."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class VisaCategory(enum.StrEnum):
    """Visa/work permit type classification."""

    FREE_MOVEMENT = "free_movement"
    WORK_PERMIT = "work_permit"
    BLUE_CARD = "blue_card"
    SKILLED_WORKER = "skilled_worker"
    INVESTOR = "investor"
    OTHER = "other"


class ComparisonStatus(enum.StrEnum):
    """Lifecycle status of a country comparison."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ── CredentialMapping ──────────────────────────────────────────


class CredentialMapping(Base, UUIDMixin, TimestampMixin):
    """Cross-Border Career Passport™ — qualification equivalency mapping.

    EQF Intelligence Engine™ — maps a source qualification to its
    international equivalent using the European Qualifications Framework
    (8 levels, Bologna-aligned). Each mapping includes:
        - Source and target country/qualification
        - EQF level alignment
        - Recognition notes and framework reference
        - Confidence score (hard-capped at 0.85)

    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "credential_mappings"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_credential_mapping_confidence_cap",
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
    source_qualification: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    source_country: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    target_country: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    equivalent_level: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    eqf_level: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True,
    )
    recognition_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    framework_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-powered credential equivalency via EQF framework",
        server_default="AI-powered credential equivalency via EQF framework",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "AI-estimated equivalency — verify with official bodies "
            "(ENIC-NARIC, national recognition centers). "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "AI-estimated equivalency — verify with official bodies "
            "(ENIC-NARIC, national recognition centers). "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="credential_mappings",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CredentialMapping(source={self.source_country}, "
            f"target={self.target_country}, eqf={self.eqf_level})>"
        )


# ── CountryComparison ──────────────────────────────────────────


class CountryComparison(Base, UUIDMixin, TimestampMixin):
    """Side-by-side country career mobility analysis.

    Purchasing Power Calculator™ — compares two countries across
    cost of living, salary delta, purchasing power, tax impact,
    and market demand for the user's role.
    """

    __tablename__ = "country_comparisons"

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
    source_country: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    target_country: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ComparisonStatus.ACTIVE.value,
        server_default="active", nullable=False,
    )

    # ── Financial analysis ──
    col_delta_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    salary_delta_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    purchasing_power_delta: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    tax_impact_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    market_demand_level: Mapped[str] = mapped_column(
        String(20), default=DemandLevel.MODERATE.value,
        server_default="moderate", nullable=False,
    )

    # ── Detailed breakdown (JSON) ──
    detailed_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed cost-of-living and salary data",
        server_default="AI-analyzed cost-of-living and salary data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Financial estimates are AI-generated approximations. "
            "Actual costs vary by lifestyle, location within country, and timing. "
            "Consult local resources for current data."
        ),
        server_default=(
            "Financial estimates are AI-generated approximations. "
            "Actual costs vary by lifestyle, location within country, and timing. "
            "Consult local resources for current data."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="country_comparisons",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CountryComparison({self.source_country}→{self.target_country}, "
            f"pp_delta={self.purchasing_power_delta}%)>"
        )


# ── VisaAssessment ─────────────────────────────────────────────


class VisaAssessment(Base, UUIDMixin, TimestampMixin):
    """Visa/work permit feasibility assessment.

    Visa Eligibility Predictor™ — AI-assessed visa category,
    eligibility scoring, requirements, processing time, and
    estimated cost for the user's nationality + target country.
    """

    __tablename__ = "visa_assessments"
    __table_args__ = (
        CheckConstraint(
            "eligibility_score <= 0.85",
            name="ck_visa_assessment_eligibility_cap",
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
    nationality: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    target_country: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    visa_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    eligibility_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    requirements: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    processing_time_weeks: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    estimated_cost: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-assessed visa feasibility based on public immigration data",
        server_default="AI-assessed visa feasibility based on public immigration data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This is NOT legal or immigration advice. Visa requirements change frequently. "
            "Consult official immigration authorities or a licensed advisor. "
            "Maximum eligibility confidence: 85%."
        ),
        server_default=(
            "This is NOT legal or immigration advice. Visa requirements change frequently. "
            "Consult official immigration authorities or a licensed advisor. "
            "Maximum eligibility confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="visa_assessments",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<VisaAssessment(nationality={self.nationality}, "
            f"target={self.target_country}, type={self.visa_type})>"
        )


# ── MarketDemandEntry ──────────────────────────────────────────


class MarketDemandEntry(Base, UUIDMixin, TimestampMixin):
    """Role demand snapshot by country.

    Provides market demand intelligence for the user's role
    in a specific country, including open positions estimate,
    year-over-year growth, and top employers.
    """

    __tablename__ = "career_passport_market_demand"

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
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    industry: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    demand_level: Mapped[str] = mapped_column(
        String(20), default=DemandLevel.MODERATE.value,
        server_default="moderate", nullable=False,
    )
    open_positions_estimate: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    yoy_growth_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    top_employers: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    salary_range_min: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    salary_range_max: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False,
    )

    # ── Transparency ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-analyzed market demand from public job data",
        server_default="AI-analyzed market demand from public job data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Market demand estimates are AI-generated approximations. "
            "Actual job availability varies. "
            "Consult local job boards for current openings."
        ),
        server_default=(
            "Market demand estimates are AI-generated approximations. "
            "Actual job availability varies. "
            "Consult local job boards for current openings."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="passport_market_demand",
    )
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<MarketDemandEntry(country={self.country}, "
            f"role={self.role}, level={self.demand_level})>"
        )


# ── CareerPassportPreference ──────────────────────────────────


class CareerPassportPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Cross-Border Career Passport™.

    Supports user autonomy (PathForge Manifesto #5):
    users control preferred target countries, nationality,
    and which analysis modules to include.
    """

    __tablename__ = "career_passport_preferences"

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
    preferred_countries: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    nationality: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    include_visa_info: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_col_comparison: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    include_market_demand: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="career_passport_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<CareerPassportPreference(user_id={self.user_id}, "
            f"nationality={self.nationality})>"
        )
