"""
PathForge — Skill Decay & Growth Tracker Schemas
===================================================
Pydantic request/response models for the Skill Decay & Growth Tracker API.
All schemas use strict typing with no `Any` fields.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Skill Freshness ────────────────────────────────────────────


class SkillFreshnessResponse(BaseModel):
    """Single skill freshness score from the Skill Half-Life Engine™."""

    id: uuid.UUID
    skill_name: str
    category: str
    last_active_date: str | None = None
    freshness_score: float = Field(ge=0.0, le=100.0)
    half_life_days: int = Field(ge=1)
    decay_rate: str
    days_since_active: int = Field(ge=0)
    refresh_urgency: float = Field(ge=0.0, le=1.0)
    analysis_reasoning: str | None = None
    computed_at: datetime

    model_config = {"from_attributes": True}


# ── Market Demand ──────────────────────────────────────────────


class MarketDemandSnapshotResponse(BaseModel):
    """Single skill market demand snapshot from Market Demand Curves™."""

    id: uuid.UUID
    skill_name: str
    demand_score: float = Field(ge=0.0, le=100.0)
    demand_trend: str
    trend_confidence: float = Field(ge=0.0, le=1.0)
    job_posting_signal: dict[str, Any] | None = None
    industry_relevance: dict[str, Any] | None = None
    growth_projection_6m: float | None = None
    growth_projection_12m: float | None = None
    data_sources: dict[str, Any] | None = None
    snapshot_date: datetime

    model_config = {"from_attributes": True}


# ── Skill Velocity ─────────────────────────────────────────────


class SkillVelocityEntryResponse(BaseModel):
    """Single skill velocity from the Skill Velocity Map™."""

    id: uuid.UUID
    skill_name: str
    velocity_score: float = Field(ge=-100.0, le=100.0)
    velocity_direction: str
    freshness_component: float | None = None
    demand_component: float | None = None
    composite_health: float = Field(ge=0.0, le=100.0)
    acceleration: float | None = None
    reasoning: str | None = None
    computed_at: datetime

    model_config = {"from_attributes": True}


# ── Reskilling Pathways ───────────────────────────────────────


class ReskillingPathwayResponse(BaseModel):
    """Single personalized reskilling pathway recommendation."""

    id: uuid.UUID
    target_skill: str
    current_level: str
    target_level: str
    priority: str
    rationale: str | None = None
    estimated_effort_hours: int | None = None
    prerequisite_skills: dict[str, Any] | None = None
    learning_resources: dict[str, Any] | None = None
    career_impact: str | None = None
    freshness_gain: float | None = None
    demand_alignment: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Preferences ────────────────────────────────────────────────


class SkillDecayPreferenceResponse(BaseModel):
    """User notification preferences for skill decay tracking."""

    id: uuid.UUID
    tracking_enabled: bool = True
    notification_frequency: str = "weekly"
    decay_alert_threshold: float = Field(ge=0.0, le=100.0, default=40.0)
    focus_categories: dict[str, Any] | None = None
    excluded_skills: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SkillDecayPreferenceUpdateRequest(BaseModel):
    """Update skill decay notification preferences (partial update)."""

    tracking_enabled: bool | None = None
    notification_frequency: str | None = None
    decay_alert_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    focus_categories: dict[str, Any] | None = None
    excluded_skills: dict[str, Any] | None = None


# ── Request Schemas ───────────────────────────────────────────


class SkillRefreshRequest(BaseModel):
    """Request to manually refresh a skill's freshness score."""

    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Skill name to mark as refreshed",
    )


# ── Composite Responses ───────────────────────────────────────


class SkillDecayScanResponse(BaseModel):
    """Response after triggering a comprehensive skill decay scan."""

    status: str = "completed"
    skills_analyzed: int = 0
    freshness: list[SkillFreshnessResponse] = Field(default_factory=list)
    market_demand: list[MarketDemandSnapshotResponse] = Field(default_factory=list)
    velocity: list[SkillVelocityEntryResponse] = Field(default_factory=list)
    reskilling_pathways: list[ReskillingPathwayResponse] = Field(default_factory=list)


class SkillDecayDashboardResponse(BaseModel):
    """Full Skill Decay & Growth Tracker dashboard overview."""

    freshness: list[SkillFreshnessResponse] = Field(default_factory=list)
    freshness_summary: dict[str, Any] = Field(default_factory=dict)
    market_demand: list[MarketDemandSnapshotResponse] = Field(default_factory=list)
    velocity: list[SkillVelocityEntryResponse] = Field(default_factory=list)
    reskilling_pathways: list[ReskillingPathwayResponse] = Field(default_factory=list)
    preference: SkillDecayPreferenceResponse | None = None
    last_scan_at: datetime | None = None
