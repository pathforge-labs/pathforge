"""
PathForge — Cross-Border Career Passport™ Schemas
===================================================
Pydantic request/response schemas for the Career Passport API.

Response Schemas (9):
    CredentialMappingResponse      — Credential equivalency detail
    CountryComparisonResponse      — Country comparison analysis
    VisaAssessmentResponse         — Visa feasibility detail
    MarketDemandResponse           — Market demand snapshot
    CareerPassportPreferenceResponse — User preferences
    CareerPassportDashboardResponse — Dashboard aggregate
    PassportScanResponse           — Full passport scan result
    MultiCountryComparisonResponse — Side-by-side comparison
    PassportScoreResponse          — Composite passport readiness score

Request Schemas (6):
    CredentialMappingRequest       — Map a qualification
    CountryComparisonRequest       — Compare two countries
    MultiCountryComparisonRequest  — Compare up to 5 countries
    VisaAssessmentRequest          — Assess visa feasibility
    MarketDemandRequest            — Get market demand
    CareerPassportPreferenceUpdate — Update preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class CredentialMappingResponse(BaseModel):
    """Credential equivalency mapping result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    source_qualification: str
    source_country: str
    target_country: str
    equivalent_level: str
    eqf_level: str
    recognition_notes: str | None = None
    framework_reference: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class CountryComparisonResponse(BaseModel):
    """Side-by-side country comparison analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    source_country: str
    target_country: str
    status: str
    col_delta_pct: float
    salary_delta_pct: float
    purchasing_power_delta: float
    tax_impact_notes: str | None = None
    market_demand_level: str
    detailed_breakdown: dict[str, object] | None = None
    data_source: str
    disclaimer: str
    created_at: datetime


class VisaAssessmentResponse(BaseModel):
    """Visa/permit feasibility assessment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    nationality: str
    target_country: str
    visa_type: str
    eligibility_score: float
    requirements: dict[str, object] | None = None
    processing_time_weeks: int | None = None
    estimated_cost: str | None = None
    notes: str | None = None
    data_source: str
    disclaimer: str
    created_at: datetime


class MarketDemandResponse(BaseModel):
    """Market demand snapshot for a role in a country."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    country: str
    role: str
    industry: str | None = None
    demand_level: str
    open_positions_estimate: int | None = None
    yoy_growth_pct: float | None = None
    top_employers: dict[str, object] | None = None
    salary_range_min: float | None = None
    salary_range_max: float | None = None
    currency: str
    data_source: str
    disclaimer: str
    created_at: datetime


class CareerPassportPreferenceResponse(BaseModel):
    """User preferences for Career Passport."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    preferred_countries: dict[str, object] | None = None
    nationality: str | None = None
    include_visa_info: bool
    include_col_comparison: bool
    include_market_demand: bool
    created_at: datetime


class PassportScoreResponse(BaseModel):
    """Composite Career Passport Score™ — mobility readiness metric."""

    credential_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Credential recognition readiness (0-1).",
    )
    visa_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Visa eligibility assessment (0-1).",
    )
    demand_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Market demand fit (0-1).",
    )
    financial_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Financial attractiveness (0-1).",
    )
    overall_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Weighted composite score (0-1).",
    )
    target_country: str
    data_source: str = "AI-computed Career Passport Score™"
    disclaimer: str = (
        "Composite score is AI-estimated. Individual components "
        "should be verified with official sources. Maximum confidence: 85%."
    )


class CareerPassportDashboardResponse(BaseModel):
    """Dashboard aggregate: mappings + comparisons + score."""

    credential_mappings: list[CredentialMappingResponse] = Field(
        default_factory=list,
    )
    country_comparisons: list[CountryComparisonResponse] = Field(
        default_factory=list,
    )
    visa_assessments: list[VisaAssessmentResponse] = Field(
        default_factory=list,
    )
    market_demand: list[MarketDemandResponse] = Field(
        default_factory=list,
    )
    preferences: CareerPassportPreferenceResponse | None = None
    passport_scores: list[PassportScoreResponse] = Field(
        default_factory=list,
    )
    data_source: str = (
        "AI-powered Cross-Border Career Passport™ intelligence"
    )
    disclaimer: str = (
        "All assessments are AI-generated estimates. "
        "Verify credentials with ENIC-NARIC, visa requirements with "
        "official immigration authorities, and financial data with local sources. "
        "Maximum confidence: 85%."
    )


class PassportScanResponse(BaseModel):
    """Full passport scan result for a target country."""

    credential_mapping: CredentialMappingResponse | None = None
    country_comparison: CountryComparisonResponse | None = None
    visa_assessment: VisaAssessmentResponse | None = None
    market_demand: MarketDemandResponse | None = None
    passport_score: PassportScoreResponse | None = None
    data_source: str = (
        "AI-powered Cross-Border Career Passport™ intelligence"
    )
    disclaimer: str = (
        "All assessments are AI-generated estimates. "
        "Verify with official bodies (ENIC-NARIC, immigration authorities). "
        "Maximum confidence: 85%."
    )


class MultiCountryComparisonResponse(BaseModel):
    """Side-by-side multi-country comparison."""

    comparisons: list[CountryComparisonResponse] = Field(
        default_factory=list,
    )
    passport_scores: list[PassportScoreResponse] = Field(
        default_factory=list,
    )
    recommended_country: str | None = None
    recommendation_reasoning: str | None = None
    data_source: str = (
        "AI-powered Cross-Border Career Passport™ intelligence"
    )
    disclaimer: str = (
        "Country recommendations are AI-generated estimates. "
        "Actual experience varies. Conduct thorough personal research. "
        "Maximum confidence: 85%."
    )


# ── Request Schemas ────────────────────────────────────────────


class CredentialMappingRequest(BaseModel):
    """Map a single qualification to target country."""

    source_qualification: str = Field(
        ..., min_length=1, max_length=500,
        description="Qualification/degree to map (e.g., 'BSc Computer Science').",
    )
    source_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Country where qualification was obtained.",
    )
    target_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Target country for equivalency mapping.",
    )


class CountryComparisonRequest(BaseModel):
    """Compare two countries for career mobility."""

    source_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Current country of residence.",
    )
    target_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Target country to compare against.",
    )


class MultiCountryComparisonRequest(BaseModel):
    """Compare up to 5 target countries."""

    source_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Current country of residence.",
    )
    target_countries: list[str] = Field(
        ..., min_length=1, max_length=5,
        description="Target countries to compare (max 5).",
    )


class VisaAssessmentRequest(BaseModel):
    """Assess visa feasibility for a target country."""

    nationality: str = Field(
        ..., min_length=1, max_length=100,
        description="User's nationality/citizenship.",
    )
    target_country: str = Field(
        ..., min_length=1, max_length=100,
        description="Target country for visa assessment.",
    )


class MarketDemandRequest(BaseModel):
    """Get market demand for a role in a country."""

    country: str = Field(
        ..., min_length=1, max_length=100,
        description="Target country.",
    )
    role: str | None = Field(
        None, max_length=255,
        description="Specific role to assess (defaults to Career DNA role).",
    )
    industry: str | None = Field(
        None, max_length=200,
        description="Industry filter.",
    )


class CareerPassportPreferenceUpdate(BaseModel):
    """Update Career Passport preferences."""

    preferred_countries: list[str] | None = Field(
        None, max_length=10,
        description="Preferred target countries (max 10).",
    )
    nationality: str | None = Field(
        None, max_length=100,
        description="User's nationality for visa assessments.",
    )
    include_visa_info: bool | None = None
    include_col_comparison: bool | None = None
    include_market_demand: bool | None = None
