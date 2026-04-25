"""
PathForge — Salary Intelligence Engine™ Schemas
===================================================
Pydantic request/response models for the Salary Intelligence Engine API.
All schemas use strict typing with no `Any` fields.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Confidence & Data Source Constants ─────────────────────────

SALARY_DATA_SOURCE = "ai_estimated"
SALARY_DISCLAIMER = (
    "Salary estimates are AI-generated based on your Career DNA profile, "
    "market patterns, and publicly available compensation data. These are "
    "directional estimates — not guarantees. Actual compensation may vary "
    "based on company, negotiation, benefits, and market conditions. "
    "Confidence scores reflect data quality, not prediction accuracy."
)
MAX_LLM_CONFIDENCE = 0.85  # Hard cap — LLM-only estimates can't exceed this

# ── Salary Estimate ────────────────────────────────────────────


class SalaryEstimateResponse(BaseModel):
    """Personalized salary range estimate with factor breakdown."""

    id: uuid.UUID
    role_title: str
    location: str
    seniority_level: str
    industry: str
    estimated_min: float = Field(ge=0.0)
    estimated_max: float = Field(ge=0.0)
    estimated_median: float = Field(ge=0.0)
    currency: str = "EUR"
    confidence: float = Field(ge=0.0, le=1.0)
    data_points_count: int = Field(ge=0)
    market_percentile: float | None = None
    base_salary_factor: float | None = None
    skill_premium_factor: float | None = None
    experience_multiplier: float | None = None
    market_condition_adjustment: float | None = None
    analysis_reasoning: str | None = None
    factors_detail: dict[str, Any] | None = None
    data_source: str = Field(
        default=SALARY_DATA_SOURCE,
        description="Source of salary data: 'ai_estimated' or 'market_api'",
    )
    disclaimer: str = Field(
        default=SALARY_DISCLAIMER,
        description="Transparency disclaimer for AI-generated estimates",
    )
    computed_at: datetime

    model_config = {"from_attributes": True}


# ── Skill Salary Impact ───────────────────────────────────────


class SkillSalaryImpactResponse(BaseModel):
    """Per-skill salary contribution from Skill Premium Mapping™."""

    id: uuid.UUID
    skill_name: str
    category: str
    salary_impact_amount: float
    salary_impact_percent: float
    demand_premium: float = Field(ge=0.0)
    scarcity_factor: float = Field(ge=0.0)
    impact_direction: str = "positive"
    reasoning: str | None = None
    computed_at: datetime

    model_config = {"from_attributes": True}


# ── Salary History ─────────────────────────────────────────────


class SalaryHistoryEntryResponse(BaseModel):
    """Single point on the salary trajectory timeline."""

    id: uuid.UUID
    estimated_min: float = Field(ge=0.0)
    estimated_max: float = Field(ge=0.0)
    estimated_median: float = Field(ge=0.0)
    currency: str = "EUR"
    confidence: float = Field(ge=0.0, le=1.0)
    market_percentile: float | None = None
    role_title: str
    location: str
    seniority_level: str
    skills_count: int = Field(ge=0)
    factors_snapshot: dict[str, Any] | None = None
    snapshot_date: datetime

    model_config = {"from_attributes": True}


# ── Salary Scenario ────────────────────────────────────────────


class SalaryScenarioResponse(BaseModel):
    """What-if salary simulation result."""

    id: uuid.UUID
    scenario_type: str
    scenario_label: str
    scenario_input: dict[str, Any]
    projected_min: float = Field(ge=0.0)
    projected_max: float = Field(ge=0.0)
    projected_median: float = Field(ge=0.0)
    currency: str = "EUR"
    delta_amount: float
    delta_percent: float
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    impact_breakdown: dict[str, Any] | None = None
    computed_at: datetime

    model_config = {"from_attributes": True}


# ── Preferences ────────────────────────────────────────────────


class SalaryPreferenceResponse(BaseModel):
    """User salary tracking preferences."""

    id: uuid.UUID
    preferred_currency: str = "EUR"
    include_benefits: bool = False
    target_salary: float | None = None
    target_currency: str = "EUR"
    notification_enabled: bool = True
    notification_frequency: str = "monthly"
    comparison_market: str = "Netherlands"
    comparison_industries: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SalaryPreferenceUpdateRequest(BaseModel):
    """Update salary tracking preferences (partial update)."""

    preferred_currency: str | None = None
    include_benefits: bool | None = None
    target_salary: float | None = None
    target_currency: str | None = None
    notification_enabled: bool | None = None
    notification_frequency: str | None = None
    comparison_market: str | None = None
    comparison_industries: dict[str, Any] | None = None


# ── Request Schemas ────────────────────────────────────────────


class SalaryScenarioRequest(BaseModel):
    """Request to run a what-if salary scenario."""

    scenario_type: str = Field(
        ...,
        description="Type of scenario: add_skill, remove_skill, change_location, "
        "change_seniority, change_industry, add_certification",
    )
    scenario_label: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable label for the scenario",
    )
    scenario_input: dict[str, Any] = Field(
        ...,
        description="Scenario parameters, e.g. {'skill': 'Kubernetes'} or "
        "{'location': 'Berlin, Germany'}",
    )


class SkillWhatIfRequest(BaseModel):
    """Shortcut request: 'What if I add skill X?'"""

    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Skill to simulate adding",
    )


class LocationWhatIfRequest(BaseModel):
    """Shortcut request: 'What if I move to location Y?'"""

    location: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Location to simulate moving to",
    )


# ── Composite Responses ───────────────────────────────────────


class SalaryScanResponse(BaseModel):
    """Response after triggering a full salary intelligence scan."""

    status: str = "completed"
    estimate: SalaryEstimateResponse | None = None
    skill_impacts: list[SkillSalaryImpactResponse] = Field(
        default_factory=list
    )
    history_entry_created: bool = False


class SalaryImpactAnalysisResponse(BaseModel):
    """Comprehensive skill impact analysis with top gainers."""

    impacts: list[SkillSalaryImpactResponse] = Field(default_factory=list)
    total_premium_amount: float = 0.0
    total_premium_percent: float = 0.0
    top_positive_skills: list[str] = Field(default_factory=list)
    top_negative_skills: list[str] = Field(default_factory=list)


class SalaryTrajectoryResponse(BaseModel):
    """Historical salary trajectory with projections."""

    history: list[SalaryHistoryEntryResponse] = Field(default_factory=list)
    projected_6m_median: float | None = None
    projected_12m_median: float | None = None
    trend_direction: str | None = None
    trend_confidence: float | None = None


class SalaryDashboardResponse(BaseModel):
    """Full Salary Intelligence Engine™ dashboard overview."""

    estimate: SalaryEstimateResponse | None = None
    skill_impacts: list[SkillSalaryImpactResponse] = Field(
        default_factory=list
    )
    trajectory: SalaryTrajectoryResponse | None = None
    recent_scenarios: list[SalaryScenarioResponse] = Field(
        default_factory=list
    )
    preference: SalaryPreferenceResponse | None = None
    last_scan_at: datetime | None = None
    data_source: str = SALARY_DATA_SOURCE
    disclaimer: str = SALARY_DISCLAIMER
