"""
PathForge — Collective Intelligence Engine™ Schemas
===================================================
Pydantic request/response schemas for the Collective Intelligence API.

Response Schemas (8):
    IndustrySnapshotResponse                  — Industry health detail
    SalaryBenchmarkResponse                   — Salary positioning detail
    PeerCohortAnalysisResponse                — Peer comparison detail
    CareerPulseResponse                       — Career Pulse Index™ score
    CollectiveIntelligencePreferenceResponse   — User preferences
    CollectiveIntelligenceDashboardResponse    — Aggregated dashboard
    IntelligenceScanResponse                   — Full intelligence scan
    IndustryComparisonResponse                 — Multi-industry comparison

Request Schemas (7):
    IndustrySnapshotRequest                   — Request industry analysis
    SalaryBenchmarkRequest                    — Request salary benchmark
    PeerCohortRequest                         — Request peer comparison
    CareerPulseRequest                        — Request Career Pulse score
    IndustryComparisonRequest                 — Compare multiple industries
    CollectiveIntelligencePreferenceUpdate     — Update preferences
    IntelligenceScanRequest                    — Full scan (optional params)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class IndustrySnapshotResponse(BaseModel):
    """Industry health snapshot result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    industry: str
    region: str
    trend_direction: str
    demand_intensity: str
    top_emerging_skills: dict[str, object] | None = None
    declining_skills: dict[str, object] | None = None
    avg_salary_range_min: float | None = None
    avg_salary_range_max: float | None = None
    currency: str
    growth_rate_pct: float | None = None
    hiring_volume_trend: str | None = None
    key_insights: dict[str, object] | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class SalaryBenchmarkResponse(BaseModel):
    """Personalized salary benchmark result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    location: str
    experience_years: int
    benchmark_min: float
    benchmark_median: float
    benchmark_max: float
    currency: str
    user_percentile: float | None = None
    skill_premium_pct: float | None = None
    experience_factor: float | None = None
    negotiation_insights: dict[str, object] | None = None
    premium_skills: dict[str, object] | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class PeerCohortAnalysisResponse(BaseModel):
    """Peer Cohort Benchmarking™ result — anonymized comparison."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    cohort_criteria: dict[str, object]
    cohort_size: int
    user_rank_percentile: float
    avg_skills_count: float
    user_skills_count: int
    avg_experience_years: float
    common_transitions: dict[str, object] | None = None
    top_differentiating_skills: dict[str, object] | None = None
    skill_gaps_vs_cohort: dict[str, object] | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class CareerPulseResponse(BaseModel):
    """Career Pulse Index™ — composite career market health score."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    pulse_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Composite career market health score (0-100).",
    )
    pulse_category: str
    trend_direction: str
    demand_component: float
    salary_component: float
    skill_relevance_component: float
    trend_component: float
    top_opportunities: dict[str, object] | None = None
    risk_factors: dict[str, object] | None = None
    recommended_actions: dict[str, object] | None = None
    summary: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class CollectiveIntelligencePreferenceResponse(BaseModel):
    """User preferences for Collective Intelligence Engine."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    include_industry_pulse: bool
    include_salary_benchmarks: bool
    include_peer_analysis: bool
    preferred_industries: dict[str, object] | None = None
    preferred_locations: dict[str, object] | None = None
    preferred_currency: str
    created_at: datetime


class CollectiveIntelligenceDashboardResponse(BaseModel):
    """Dashboard aggregate: pulse + industry + salary + peer + prefs."""

    latest_pulse: CareerPulseResponse | None = None
    industry_snapshots: list[IndustrySnapshotResponse] = Field(
        default_factory=list,
    )
    salary_benchmarks: list[SalaryBenchmarkResponse] = Field(
        default_factory=list,
    )
    peer_cohort_analyses: list[PeerCohortAnalysisResponse] = Field(
        default_factory=list,
    )
    preferences: CollectiveIntelligencePreferenceResponse | None = None
    data_source: str = (
        "AI-powered Collective Intelligence Engine™"
    )
    disclaimer: str = (
        "All intelligence is AI-generated from public market data "
        "personalized to your Career DNA. No individual user data is "
        "aggregated or shared. Maximum confidence: 85%."
    )


class IntelligenceScanResponse(BaseModel):
    """Full intelligence scan result."""

    career_pulse: CareerPulseResponse | None = None
    industry_snapshot: IndustrySnapshotResponse | None = None
    salary_benchmark: SalaryBenchmarkResponse | None = None
    peer_cohort: PeerCohortAnalysisResponse | None = None
    data_source: str = (
        "AI-powered Collective Intelligence Engine™"
    )
    disclaimer: str = (
        "Full intelligence scan combines multiple AI analyses. "
        "Each component should be verified independently. "
        "Maximum confidence: 85%."
    )


class IndustryComparisonResponse(BaseModel):
    """Multi-industry comparison result."""

    snapshots: list[IndustrySnapshotResponse] = Field(
        default_factory=list,
    )
    recommended_industry: str | None = None
    recommendation_reasoning: str | None = None
    data_source: str = (
        "AI-powered Collective Intelligence Engine™"
    )
    disclaimer: str = (
        "Industry comparisons are AI-generated estimates. "
        "Actual industry conditions vary. Conduct thorough personal "
        "research. Maximum confidence: 85%."
    )


# ── Request Schemas ────────────────────────────────────────────


class IndustrySnapshotRequest(BaseModel):
    """Request an industry analysis."""

    industry: str = Field(
        ..., min_length=1, max_length=200,
        description="Industry to analyze (e.g., 'Software Development').",
    )
    region: str = Field(
        ..., min_length=1, max_length=100,
        description="Region for analysis (e.g., 'Netherlands').",
    )


class SalaryBenchmarkRequest(BaseModel):
    """Request a salary benchmark."""

    role: str | None = Field(
        None, max_length=255,
        description="Role to benchmark (defaults to Career DNA role).",
    )
    location: str | None = Field(
        None, max_length=200,
        description="Location for benchmark (defaults to Career DNA location).",
    )
    experience_years: int | None = Field(
        None, ge=0, le=50,
        description="Years of experience (defaults to Career DNA data).",
    )
    currency: str = Field(
        "EUR", max_length=10,
        description="Preferred currency for salary data.",
    )


class PeerCohortRequest(BaseModel):
    """Request a peer cohort analysis."""

    role: str | None = Field(
        None, max_length=255,
        description="Role for cohort matching (defaults to Career DNA role).",
    )
    experience_range_min: int | None = Field(
        None, ge=0,
        description="Min years experience for cohort (defaults to ±2 of user).",
    )
    experience_range_max: int | None = Field(
        None, ge=0,
        description="Max years experience for cohort.",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region filter for cohort.",
    )


class CareerPulseRequest(BaseModel):
    """Request a Career Pulse Index™ calculation."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override (defaults to Career DNA industry).",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region override (defaults to Career DNA location).",
    )


class IndustryComparisonRequest(BaseModel):
    """Compare up to 5 industries."""

    industries: list[str] = Field(
        ..., min_length=2, max_length=5,
        description="Industries to compare (2-5).",
    )
    region: str = Field(
        ..., min_length=1, max_length=100,
        description="Region for comparison.",
    )


class CollectiveIntelligencePreferenceUpdate(BaseModel):
    """Update Collective Intelligence preferences."""

    include_industry_pulse: bool | None = None
    include_salary_benchmarks: bool | None = None
    include_peer_analysis: bool | None = None
    preferred_industries: list[str] | None = Field(
        None, max_length=10,
        description="Preferred industries (max 10).",
    )
    preferred_locations: list[str] | None = Field(
        None, max_length=10,
        description="Preferred locations (max 10).",
    )
    preferred_currency: str | None = Field(
        None, max_length=10,
        description="Preferred currency for salary data.",
    )


class IntelligenceScanRequest(BaseModel):
    """Full intelligence scan with optional parameters."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override for scan.",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region override for scan.",
    )
    currency: str = Field(
        "EUR", max_length=10,
        description="Preferred currency.",
    )
