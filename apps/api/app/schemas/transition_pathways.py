"""
PathForge — Transition Pathways Schemas
==========================================
Pydantic schemas for the Transition Pathways API.

Request/response validation with strict typing, transparency
fields (data_source, disclaimer), and confidence clamping.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class SkillBridgeEntryResponse(BaseModel):
    """Individual skill gap entry in the Skill Bridge Matrix™."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    category: str
    is_already_held: bool
    current_level: str | None = None
    required_level: str | None = None
    acquisition_method: str | None = None
    estimated_weeks: int | None = None
    recommended_resources: dict[str, Any] | None = None
    priority: str
    impact_on_confidence: float | None = None


class TransitionMilestoneResponse(BaseModel):
    """Action plan milestone in the Transition Timeline Engine™."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phase: str
    title: str
    description: str | None = None
    target_week: int
    order_index: int
    is_completed: bool
    completed_at: datetime | None = None


class TransitionComparisonResponse(BaseModel):
    """Source vs target role comparison dimension."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dimension: str
    source_value: float
    target_value: float
    delta: float
    unit: str | None = None
    reasoning: str | None = None


class TransitionPathResponse(BaseModel):
    """Full transition path with Transition Confidence Score™."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    from_role: str
    to_role: str
    confidence_score: float
    difficulty: str
    status: str
    skill_overlap_percent: float
    skills_to_acquire_count: int
    estimated_duration_months: int | None = None
    optimistic_months: int | None = None
    realistic_months: int | None = None
    conservative_months: int | None = None
    salary_impact_percent: float | None = None
    success_probability: float
    reasoning: str | None = None
    factors: dict[str, Any] | None = None
    data_source: str
    disclaimer: str
    computed_at: datetime


class TransitionSummaryResponse(BaseModel):
    """Lightweight transition card for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_role: str
    to_role: str
    confidence_score: float
    difficulty: str
    status: str
    skill_overlap_percent: float
    estimated_duration_months: int | None = None
    computed_at: datetime


class TransitionPreferenceResponse(BaseModel):
    """User transition preference state."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    preferred_industries: list[str] | None = None
    excluded_roles: list[str] | None = None
    min_confidence: float
    max_timeline_months: int
    notification_enabled: bool


# ── Request Schemas ────────────────────────────────────────────


class TransitionExploreRequest(BaseModel):
    """Request to explore a career transition to a target role."""

    target_role: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Target role to explore transition to",
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


class TransitionCompareRequest(BaseModel):
    """Request to compare current role against multiple targets."""

    target_roles: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Target roles to compare (max 5)",
    )


class RoleWhatIfRequest(BaseModel):
    """Quick exploration: 'What if I moved to role X?'"""

    target_role: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Target role for what-if analysis",
    )


class TransitionPreferenceUpdateRequest(BaseModel):
    """Partial update for transition preferences."""

    preferred_industries: list[str] | None = None
    excluded_roles: list[str] | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    max_timeline_months: int | None = Field(None, ge=1, le=120)
    notification_enabled: bool | None = None


# ── Composite Response Schemas ─────────────────────────────────


class TransitionScanResponse(BaseModel):
    """Full pipeline result: path + skills + milestones + comparison."""

    transition_path: TransitionPathResponse
    skill_bridge: list[SkillBridgeEntryResponse]
    milestones: list[TransitionMilestoneResponse]
    comparisons: list[TransitionComparisonResponse]


class TransitionDashboardResponse(BaseModel):
    """All saved transitions + preferences for the dashboard."""

    transitions: list[TransitionSummaryResponse]
    preferences: TransitionPreferenceResponse | None = None
    total_explored: int
