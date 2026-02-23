"""
PathForge — Career Action Planner™ Schemas
=============================================
Pydantic v2 request/response schemas for the Career Action Planner API.

Response Schemas (9):
    CareerActionPlanResponse         — Full plan with milestones
    PlanMilestoneResponse            — Individual milestone detail
    MilestoneProgressResponse        — Progress entry detail
    PlanRecommendationResponse       — AI recommendation with source engine
    CareerActionPlannerPreferenceResponse — User preferences
    PlanDashboardResponse             — Dashboard overview
    PlanScanResponse                  — Full scan result after generation
    PlanSummaryResponse               — Abbreviated for lists
    PlanStatsResponse                 — Aggregate stats

Request Schemas (5):
    GeneratePlanRequest               — Generate new plan
    UpdatePlanStatusRequest           — Update plan status
    UpdateMilestoneRequest            — Update milestone
    LogProgressRequest                — Log progress entry
    CareerActionPlannerPreferenceUpdate — Update preferences
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class MilestoneProgressResponse(BaseModel):
    """Progress entry detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    milestone_id: uuid.UUID
    progress_percent: float = Field(ge=0.0, le=100.0)
    notes: str | None = None
    evidence_url: str | None = None
    logged_at: datetime
    created_at: datetime


class PlanMilestoneResponse(BaseModel):
    """Individual milestone with progress summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    title: str
    description: str | None = None
    category: str
    target_date: date | None = None
    status: str
    effort_hours: int
    priority: int = Field(ge=1, le=10)
    evidence_required: str | None = None
    progress_entries: list[MilestoneProgressResponse] = Field(
        default_factory=list,
    )
    created_at: datetime


class PlanRecommendationResponse(BaseModel):
    """AI recommendation from intelligence engine."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    source_engine: str
    recommendation_type: str
    title: str
    rationale: str
    urgency: str
    impact_score: float = Field(ge=0.0, le=100.0)
    linked_entity_id: str | None = None
    context_data: dict[str, object] | None = None
    created_at: datetime


class CareerActionPlanResponse(BaseModel):
    """Full career action plan with milestones and recommendations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    career_dna_id: uuid.UUID
    title: str
    objective: str
    plan_type: str
    status: str
    priority_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=0.85)
    data_source: str
    disclaimer: str
    milestones: list[PlanMilestoneResponse] = Field(
        default_factory=list,
    )
    recommendations: list[PlanRecommendationResponse] = Field(
        default_factory=list,
    )
    created_at: datetime


class PlanSummaryResponse(BaseModel):
    """Abbreviated plan for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    plan_type: str
    status: str
    priority_score: float
    confidence: float
    milestone_count: int = 0
    completed_milestone_count: int = 0
    created_at: datetime


class PlanStatsResponse(BaseModel):
    """Aggregate statistics across all plans."""

    total_plans: int = 0
    active_plans: int = 0
    completed_plans: int = 0
    total_milestones: int = 0
    completed_milestones: int = 0
    overall_progress_percent: float = 0.0


class CareerActionPlannerPreferenceResponse(BaseModel):
    """User preferences for Career Action Planner."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    preferred_sprint_length_weeks: int
    max_milestones_per_plan: int
    focus_areas: dict[str, object] | None = None
    notification_frequency: str
    auto_generate_recommendations: bool
    created_at: datetime


class PlanDashboardResponse(BaseModel):
    """Dashboard overview: active plans, stats, recommendations."""

    active_plans: list[PlanSummaryResponse] = Field(
        default_factory=list,
    )
    recent_recommendations: list[PlanRecommendationResponse] = Field(
        default_factory=list,
    )
    stats: PlanStatsResponse = Field(
        default_factory=PlanStatsResponse,
    )
    preferences: CareerActionPlannerPreferenceResponse | None = None
    disclaimer: str = (
        "All career action plans are AI-generated suggestions. "
        "Milestones are editable and non-binding. "
        "Verify with professional career advisors. "
        "Maximum confidence: 85%."
    )


class PlanScanResponse(BaseModel):
    """Full scan result after plan generation."""

    plan: CareerActionPlanResponse
    recommendations: list[PlanRecommendationResponse] = Field(
        default_factory=list,
    )
    disclaimer: str = (
        "AI-generated career action plan based on Career DNA™ intelligence. "
        "All milestones are suggestions and should be reviewed before commitment. "
        "Maximum confidence: 85%."
    )


class PlanComparisonResponse(BaseModel):
    """Compare multiple plan scenarios."""

    plans: list[CareerActionPlanResponse] = Field(
        default_factory=list,
    )
    recommended_plan_id: uuid.UUID | None = None
    recommendation_reasoning: str | None = None
    disclaimer: str = (
        "Plan comparison is AI-generated. "
        "Consider personal preferences and circumstances. "
        "Maximum confidence: 85%."
    )


# ── Request Schemas ────────────────────────────────────────────


class GeneratePlanRequest(BaseModel):
    """Request to generate a new career action plan."""

    plan_type: str = Field(
        ..., min_length=1, max_length=30,
        description=(
            "Plan type: skill_development, role_transition, "
            "salary_growth, threat_mitigation, or opportunity_capture."
        ),
    )
    focus_area: str | None = Field(
        None, max_length=300,
        description="Optional focus area to narrow the plan scope.",
    )
    target_timeline_weeks: int = Field(
        default=4, ge=1, le=12,
        description="Target timeline in weeks (1-12).",
    )


class UpdatePlanStatusRequest(BaseModel):
    """Request to update plan status."""

    status: str = Field(
        ..., min_length=1, max_length=20,
        description=(
            "New status: active, paused, completed, or archived."
        ),
    )


class UpdateMilestoneRequest(BaseModel):
    """Request to update a milestone."""

    status: str | None = Field(
        None, max_length=20,
        description="New status: in_progress, completed, skipped, blocked.",
    )
    target_date: date | None = Field(
        None,
        description="Updated target date.",
    )
    effort_hours: int | None = Field(
        None, ge=0,
        description="Updated effort estimate in hours.",
    )
    priority: int | None = Field(
        None, ge=1, le=10,
        description="Updated priority (1-10).",
    )


class LogProgressRequest(BaseModel):
    """Request to log progress against a milestone."""

    progress_percent: float = Field(
        ..., ge=0.0, le=100.0,
        description="Current progress percentage (0-100).",
    )
    notes: str | None = Field(
        None, max_length=2000,
        description="Progress notes.",
    )
    evidence_url: str | None = Field(
        None, max_length=500,
        description="URL to evidence (certificate, portfolio, etc.).",
    )


class CareerActionPlannerPreferenceUpdate(BaseModel):
    """Update preferences for Career Action Planner."""

    preferred_sprint_length_weeks: int | None = Field(
        None, ge=1, le=12,
        description="Preferred sprint length in weeks.",
    )
    max_milestones_per_plan: int | None = Field(
        None, ge=1, le=10,
        description="Maximum milestones per plan.",
    )
    focus_areas: dict[str, object] | None = Field(
        None,
        description="Preferred focus areas for plan generation.",
    )
    notification_frequency: str | None = Field(
        None, max_length=20,
        description="Notification frequency: daily, weekly, biweekly.",
    )
    auto_generate_recommendations: bool | None = Field(
        None,
        description="Auto-generate recommendations from intelligence engines.",
    )
