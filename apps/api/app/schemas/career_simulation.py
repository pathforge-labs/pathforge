"""
PathForge — Career Simulation Engine™ Schemas
================================================
Request/response Pydantic schemas for the Career Simulation API.

Request schemas validate user input with constraints.
Response schemas provide full transparency (data_source, disclaimer).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ─────────────────────────────────────────


class SimulationInputResponse(BaseModel):
    """A single input parameter key-value pair."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parameter_name: str
    parameter_value: str
    parameter_type: str


class SimulationOutcomeResponse(BaseModel):
    """A single dimension projection (current → projected → delta)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dimension: str
    current_value: float
    projected_value: float
    delta: float
    unit: str | None = None
    reasoning: str | None = None


class SimulationRecommendationResponse(BaseModel):
    """A single actionable recommendation with priority."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    priority: str
    title: str
    description: str | None = None
    estimated_weeks: int | None = None
    order_index: int


class CareerSimulationResponse(BaseModel):
    """Full simulation detail with all projections and recommendations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    scenario_type: str
    status: str
    confidence_score: float
    feasibility_rating: float
    roi_score: float | None = None
    salary_impact_percent: float | None = None
    estimated_months: int | None = None
    reasoning: str | None = None
    factors: dict[str, Any] | None = None
    data_source: str
    disclaimer: str
    computed_at: datetime
    inputs: list[SimulationInputResponse] = Field(default_factory=list)
    outcomes: list[SimulationOutcomeResponse] = Field(default_factory=list)
    recommendations: list[SimulationRecommendationResponse] = Field(default_factory=list)


class SimulationSummaryResponse(BaseModel):
    """Lightweight simulation card for list views and dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_type: str
    status: str
    confidence_score: float
    salary_impact_percent: float | None = None
    estimated_months: int | None = None
    data_source: str
    disclaimer: str
    computed_at: datetime


class SimulationPreferenceResponse(BaseModel):
    """User preferences for the simulation module."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    default_scenario_type: str | None = None
    max_scenarios: int
    notification_enabled: bool


class SimulationComparisonResponse(BaseModel):
    """Side-by-side comparison of multiple simulations."""

    model_config = ConfigDict(from_attributes=True)

    simulations: list[CareerSimulationResponse]
    ranking: list[uuid.UUID] = Field(
        default_factory=list,
        description="Simulation IDs ranked by composite desirability",
    )
    trade_off_analysis: str | None = None
    data_source: str = "AI-generated comparison based on Career DNA and market data"
    disclaimer: str = (
        "This comparison is an AI-generated analysis, not a guarantee. "
        "Actual outcomes depend on market conditions, personal effort, "
        "and factors beyond prediction."
    )


class SimulationDashboardResponse(BaseModel):
    """Dashboard: all simulations + preferences + summary stats."""

    simulations: list[SimulationSummaryResponse] = Field(default_factory=list)
    preferences: SimulationPreferenceResponse | None = None
    total_simulations: int = 0
    scenario_type_counts: dict[str, int] = Field(default_factory=dict)


# ── Request Schemas ──────────────────────────────────────────


class RoleTransitionSimRequest(BaseModel):
    """What-if: role transition scenario."""

    target_role: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Target role to simulate transition to",
    )
    target_industry: str | None = Field(
        None,
        max_length=255,
        description="Optional target industry for context",
    )
    target_location: str | None = Field(
        None,
        max_length=255,
        description="Optional target location for context",
    )


class GeoMoveSimRequest(BaseModel):
    """What-if: geographic relocation scenario."""

    target_location: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Target location to simulate moving to",
    )
    keep_role: bool = Field(
        True,
        description="Whether to keep the same role after the move",
    )
    target_role: str | None = Field(
        None,
        max_length=255,
        description="Optional new role in the target location",
    )


class SkillInvestmentSimRequest(BaseModel):
    """What-if: skill investment scenario."""

    skills: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Skills to simulate investing in (1-10)",
    )
    target_role: str | None = Field(
        None,
        max_length=255,
        description="Optional target role that benefits from these skills",
    )


class IndustryPivotSimRequest(BaseModel):
    """What-if: industry pivot scenario."""

    target_industry: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Target industry to pivot to",
    )
    target_role: str | None = Field(
        None,
        max_length=255,
        description="Optional target role in that industry",
    )


class SeniorityJumpSimRequest(BaseModel):
    """What-if: seniority level change scenario."""

    target_seniority: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target seniority level (e.g. 'Lead', 'Staff', 'Director')",
    )
    target_role: str | None = Field(
        None,
        max_length=255,
        description="Optional specific role at that seniority",
    )


class SimulationCompareRequest(BaseModel):
    """Request to compare multiple saved simulations."""

    simulation_ids: list[uuid.UUID] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2-5 simulation IDs to compare side-by-side",
    )


class SimulationPreferenceUpdateRequest(BaseModel):
    """Partial update for simulation preferences."""

    default_scenario_type: str | None = None
    max_scenarios: int | None = Field(None, ge=1, le=100)
    notification_enabled: bool | None = None
