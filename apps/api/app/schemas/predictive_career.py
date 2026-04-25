"""
PathForge — Predictive Career Engine™ Schemas
==============================================
Pydantic request/response schemas for the Predictive Career Engine API.

Response Schemas (7):
    EmergingRoleResponse                   — Emerging role detail
    DisruptionForecastResponse             — Disruption prediction detail
    OpportunitySurfaceResponse             — Surfaced opportunity detail
    CareerForecastResponse                 — Career Forecast Index™ score
    PredictiveCareerPreferenceResponse     — User preferences
    PredictiveCareerDashboardResponse      — Aggregated dashboard
    PredictiveScanResponse                 — Full predictive scan

Request Schemas (3):
    PredictiveCareerScanRequest            — Full scan parameters
    EmergingRoleRequest                    — Request emerging role analysis
    PredictiveCareerPreferenceUpdate       — Update preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class EmergingRoleResponse(BaseModel):
    """Emerging Role Radar™ — detected emerging role opportunity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    role_title: str
    industry: str
    emergence_stage: str
    growth_rate_pct: float
    skill_overlap_pct: float
    time_to_mainstream_months: int | None = None
    required_new_skills: dict[str, object] | None = None
    transferable_skills: dict[str, object] | None = None
    avg_salary_range_min: float | None = None
    avg_salary_range_max: float | None = None
    key_employers: dict[str, object] | None = None
    reasoning: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class DisruptionForecastResponse(BaseModel):
    """Disruption Forecast Engine™ — disruption prediction detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    disruption_title: str
    disruption_type: str
    industry: str
    severity_score: float
    timeline_months: int
    impact_on_user: str | None = None
    affected_skills: dict[str, object] | None = None
    mitigation_strategies: dict[str, object] | None = None
    opportunity_from_disruption: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class OpportunitySurfaceResponse(BaseModel):
    """Proactive Opportunity Surfacing — surfaced opportunity detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    opportunity_title: str
    opportunity_type: str
    source_signal: str
    relevance_score: float
    action_items: dict[str, object] | None = None
    required_skills: dict[str, object] | None = None
    skill_gap_analysis: dict[str, object] | None = None
    time_sensitivity: str | None = None
    reasoning: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class CareerForecastResponse(BaseModel):
    """Career Forecast Index™ — composite forward-looking career score."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    outlook_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Composite forward-looking career outlook score (0-100).",
    )
    outlook_category: str
    forecast_horizon_months: int
    role_component: float
    disruption_component: float
    opportunity_component: float
    trend_component: float
    top_actions: dict[str, object] | None = None
    key_risks: dict[str, object] | None = None
    key_opportunities: dict[str, object] | None = None
    summary: str | None = None
    confidence_score: float
    data_source: str
    disclaimer: str
    created_at: datetime


class PredictiveCareerPreferenceResponse(BaseModel):
    """User preferences for Predictive Career Engine."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    forecast_horizon_months: int
    include_emerging_roles: bool
    include_disruption_alerts: bool
    include_opportunities: bool
    risk_tolerance: str
    focus_industries: dict[str, object] | None = None
    focus_regions: dict[str, object] | None = None
    created_at: datetime


class PredictiveCareerDashboardResponse(BaseModel):
    """Dashboard aggregate: forecast + roles + disruptions + opportunities."""

    latest_forecast: CareerForecastResponse | None = None
    emerging_roles: list[EmergingRoleResponse] = Field(
        default_factory=list,
    )
    disruption_forecasts: list[DisruptionForecastResponse] = Field(
        default_factory=list,
    )
    opportunity_surfaces: list[OpportunitySurfaceResponse] = Field(
        default_factory=list,
    )
    preferences: PredictiveCareerPreferenceResponse | None = None
    data_source: str = (
        "AI-powered Predictive Career Engine™"
    )
    disclaimer: str = (
        "All predictions are AI-generated from public market data "
        "personalized to your Career DNA. These are forecasts, not "
        "guarantees. Maximum confidence: 85%."
    )


class PredictiveScanResponse(BaseModel):
    """Full predictive scan result."""

    career_forecast: CareerForecastResponse | None = None
    emerging_roles: list[EmergingRoleResponse] = Field(
        default_factory=list,
    )
    disruption_forecasts: list[DisruptionForecastResponse] = Field(
        default_factory=list,
    )
    opportunity_surfaces: list[OpportunitySurfaceResponse] = Field(
        default_factory=list,
    )
    data_source: str = (
        "AI-powered Predictive Career Engine™"
    )
    disclaimer: str = (
        "Full predictive scan combines multiple AI analyses. "
        "Each component should be verified independently. "
        "Maximum confidence: 85%."
    )


# ── Request Schemas ────────────────────────────────────────────


class PredictiveCareerScanRequest(BaseModel):
    """Full predictive scan with optional parameters."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override for scan.",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region override for scan.",
    )
    forecast_horizon_months: int = Field(
        12, ge=3, le=36,
        description="Forecast horizon in months (3-36).",
    )


class EmergingRoleRequest(BaseModel):
    """Request emerging role analysis."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override (defaults to Career DNA industry).",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region override (defaults to Career DNA location).",
    )
    min_skill_overlap_pct: float = Field(
        50.0, ge=0.0, le=100.0,
        description="Minimum skill overlap percentage (default 50%).",
    )


class DisruptionForecastRequest(BaseModel):
    """Request disruption forecasting."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override for disruption analysis.",
    )
    forecast_horizon_months: int = Field(
        12, ge=3, le=36,
        description="Forecast horizon in months (3-36).",
    )


class OpportunitySurfaceRequest(BaseModel):
    """Request opportunity surfacing."""

    industry: str | None = Field(
        None, max_length=200,
        description="Industry override for opportunity surfacing.",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Region override.",
    )
    include_cross_border: bool = Field(
        True,
        description="Include cross-border opportunities.",
    )


class PredictiveCareerPreferenceUpdate(BaseModel):
    """Update Predictive Career Engine preferences."""

    forecast_horizon_months: int | None = Field(
        None, ge=3, le=36,
        description="Forecast horizon in months (3-36).",
    )
    include_emerging_roles: bool | None = None
    include_disruption_alerts: bool | None = None
    include_opportunities: bool | None = None
    risk_tolerance: str | None = Field(
        None,
        description="Risk tolerance: conservative, moderate, aggressive.",
    )
    focus_industries: list[str] | None = Field(
        None, max_length=10,
        description="Focus industries (max 10).",
    )
    focus_regions: list[str] | None = Field(
        None, max_length=10,
        description="Focus regions (max 10).",
    )
