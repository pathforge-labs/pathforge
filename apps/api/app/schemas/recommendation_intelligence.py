"""
PathForge — Cross-Engine Recommendation Intelligence™ Schemas
==============================================================
Pydantic request/response schemas for the Recommendation Intelligence API.

Response Schemas (8):
    CrossEngineRecommendationResponse  — Full recommendation with scoring
    RecommendationCorrelationResponse  — Engine contribution mapping
    RecommendationBatchResponse        — Batch analysis run summary
    RecommendationDashboardResponse    — Dashboard with latest batch + stats
    RecommendationPreferenceResponse   — User preference settings
    RecommendationSummary              — Lightweight recommendation overview
    PriorityBreakdown                  — Priority score decomposition
    EngineCorrelation                  — Engine correlation detail

Request Schemas (3):
    GenerateRecommendationsRequest     — Trigger recommendation generation
    UpdateRecommendationStatusRequest  — Update recommendation lifecycle
    RecommendationPreferenceUpdate     — Update filtering preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Internal Schemas ──────────────────────────────────────────


class PriorityBreakdown(BaseModel):
    """Priority-Weighted Score™ decomposition."""

    urgency: float = Field(
        ..., ge=0.0, le=100.0,
        description="Urgency component (weight: 0.40).",
    )
    impact: float = Field(
        ..., ge=0.0, le=100.0,
        description="Impact component (weight: 0.35).",
    )
    effort_level: str = Field(
        ...,
        description="quick_win | moderate | significant | major_initiative",
    )
    inverse_effort: float = Field(
        ..., ge=0.0, le=100.0,
        description="Inverse effort component (weight: 0.25).",
    )
    final_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Priority-Weighted Score™ (0-100).",
    )


class EngineCorrelation(BaseModel):
    """Engine contribution to a recommendation."""

    engine_name: str
    display_name: str
    correlation_strength: float = Field(
        ..., ge=0.0, le=1.0,
        description="Strength of engine's contribution (0.0-1.0).",
    )
    insight_summary: str = Field(
        "",
        description="Brief summary of what this engine contributed.",
    )


# ── Response Schemas ─────────────────────────────────────────


class RecommendationCorrelationResponse(BaseModel):
    """Cross-Engine Correlation Map™ — engine-to-recommendation mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommendation_id: uuid.UUID
    engine_name: str
    correlation_strength: float = Field(
        ..., ge=0.0, le=1.0,
    )
    insight_summary: str
    created_at: datetime


class CrossEngineRecommendationResponse(BaseModel):
    """Intelligence Fusion Engine™ — full recommendation with scoring."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    recommendation_type: str = Field(
        ...,
        description=(
            "skill_gap | threat_mitigation | opportunity | "
            "salary_optimization | career_acceleration | network_building"
        ),
    )
    status: str = Field(
        ...,
        description="pending | in_progress | completed | dismissed | expired",
    )
    effort_level: str = Field(
        ...,
        description="quick_win | moderate | significant | major_initiative",
    )
    priority_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Priority-Weighted Score™ (0-100).",
    )
    urgency: float = Field(..., ge=0.0, le=100.0)
    impact_score: float = Field(..., ge=0.0, le=100.0)
    confidence_score: float = Field(
        ..., ge=0.0, le=0.85,
        description="AI confidence (capped at 0.85).",
    )
    title: str
    description: str
    action_items: list[str] | None = None
    source_engines: list[str] | None = None
    data_source: str
    disclaimer: str
    created_at: datetime
    updated_at: datetime


class RecommendationSummary(BaseModel):
    """Lightweight recommendation overview for lists."""

    id: uuid.UUID
    recommendation_type: str
    status: str
    priority_score: float = Field(..., ge=0.0, le=100.0)
    effort_level: str
    title: str
    confidence_score: float = Field(..., ge=0.0, le=0.85)
    created_at: datetime


class RecommendationBatchResponse(BaseModel):
    """Intelligence Fusion Engine™ — batch analysis run summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    batch_type: str
    total_recommendations: int
    career_vitals_at_generation: float | None = None
    data_source: str
    created_at: datetime
    updated_at: datetime


class RecommendationPreferenceResponse(BaseModel):
    """User preference settings for Recommendation Intelligence."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    enabled_categories: list[str] | None = None
    min_priority_threshold: float = Field(
        0.0, ge=0.0, le=100.0,
    )
    max_recommendations_per_batch: int = Field(10, ge=1, le=50)
    preferred_effort_levels: list[str] | None = None
    notifications_enabled: bool = True
    created_at: datetime
    updated_at: datetime


class RecommendationDashboardResponse(BaseModel):
    """Cross-Engine Recommendation Intelligence™ dashboard."""

    latest_batch: RecommendationBatchResponse | None = None
    recent_recommendations: list[RecommendationSummary] = Field(
        default_factory=list,
    )
    total_pending: int = 0
    total_in_progress: int = 0
    total_completed: int = 0
    preferences: RecommendationPreferenceResponse | None = None
    data_source: str = (
        "Intelligence Fusion Engine™ — cross-engine recommendations"
    )
    disclaimer: str = (
        "Recommendations are AI-generated by correlating signals from "
        "multiple intelligence engines. Priority scores are estimates, "
        "not guarantees. Use alongside your own judgment."
    )


# ── Request Schemas ──────────────────────────────────────────


class GenerateRecommendationsRequest(BaseModel):
    """Trigger recommendation generation from Intelligence Fusion Engine™."""

    batch_type: str = Field(
        "manual",
        description="manual | scheduled | trigger",
    )
    focus_categories: list[str] | None = Field(
        None,
        description="Optional: limit to specific recommendation types.",
    )


class UpdateRecommendationStatusRequest(BaseModel):
    """Update recommendation lifecycle status."""

    status: str = Field(
        ...,
        description="pending | in_progress | completed | dismissed",
    )
    notes: str | None = Field(
        None, max_length=1000,
        description="Optional notes about the status change.",
    )


class RecommendationPreferenceUpdate(BaseModel):
    """Update Recommendation Intelligence preferences."""

    enabled_categories: list[str] | None = Field(
        None,
        description="Recommendation types to enable. Null means all enabled.",
    )
    min_priority_threshold: float | None = Field(
        None, ge=0.0, le=100.0,
        description="Minimum priority score to surface (0-100).",
    )
    max_recommendations_per_batch: int | None = Field(
        None, ge=1, le=50,
        description="Max recommendations per generation run (1-50).",
    )
    preferred_effort_levels: list[str] | None = Field(
        None,
        description="Preferred effort levels filter.",
    )
    notifications_enabled: bool | None = Field(
        None,
        description="Enable/disable recommendation notifications.",
    )
