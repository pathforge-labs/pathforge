"""
PathForge — Hidden Job Market Detector™ Schemas
=================================================
Pydantic request/response schemas for the Hidden Job Market API.

Response Schemas (9):
    CompanySignalResponse          — Full signal detail
    CompanySignalSummaryResponse   — Lightweight card for lists
    SignalMatchResultResponse      — Career DNA ↔ signal match
    OutreachTemplateResponse       — Generated outreach message
    HiddenOpportunityResponse      — Surfaced pre-listing opportunity
    HiddenJobMarketPreferenceResponse — Monitoring preferences
    HiddenJobMarketDashboardResponse  — Dashboard aggregate
    SignalComparisonResponse       — Side-by-side signal comparison
    OpportunityRadarResponse       — Aggregated opportunity landscape

Request Schemas (6):
    ScanCompanyRequest             — Scan a specific company
    ScanIndustryRequest            — Scan an industry
    GenerateOutreachRequest        — Generate outreach for a signal
    HiddenJobMarketPreferenceUpdateRequest — Update preferences
    SignalCompareRequest           — Compare multiple signals
    DismissSignalRequest           — Dismiss or action a signal
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class SignalMatchResultResponse(BaseModel):
    """Career DNA ↔ signal match analysis result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal_id: uuid.UUID
    match_score: float
    skill_overlap: float
    role_relevance: float
    explanation: str | None = None
    matched_skills: dict[str, object] | None = None
    relevance_reasoning: str | None = None
    created_at: datetime


class OutreachTemplateResponse(BaseModel):
    """AI-generated proactive outreach message."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal_id: uuid.UUID
    template_type: str
    tone: str
    subject_line: str
    body: str
    personalization_points: dict[str, object] | None = None
    confidence: float
    created_at: datetime


class HiddenOpportunityResponse(BaseModel):
    """Surfaced pre-listing opportunity from signal analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal_id: uuid.UUID
    predicted_role: str
    predicted_seniority: str | None = None
    predicted_timeline_days: int | None = None
    probability: float
    reasoning: str | None = None
    required_skills: dict[str, object] | None = None
    salary_range_min: float | None = None
    salary_range_max: float | None = None
    currency: str
    created_at: datetime


class CompanySignalResponse(BaseModel):
    """Full company signal detail with match results and outreach."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    signal_type: str
    title: str
    description: str | None = None
    strength: float
    source: str | None = None
    source_url: str | None = None
    status: str
    confidence_score: float
    detected_at: datetime
    expires_at: datetime | None = None
    data_source: str
    disclaimer: str
    match_results: list[SignalMatchResultResponse] = Field(default_factory=list)
    outreach_templates: list[OutreachTemplateResponse] = Field(default_factory=list)
    hidden_opportunities: list[HiddenOpportunityResponse] = Field(default_factory=list)
    created_at: datetime


class CompanySignalSummaryResponse(BaseModel):
    """Lightweight signal card for dashboard lists."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    signal_type: str
    title: str
    strength: float
    status: str
    confidence_score: float
    detected_at: datetime
    match_score: float | None = None


class HiddenJobMarketPreferenceResponse(BaseModel):
    """User monitoring preferences for the Hidden Job Market Detector."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    min_signal_strength: float
    enabled_signal_types: dict[str, object] | None = None
    max_outreach_per_week: int
    auto_generate_outreach: bool
    notification_enabled: bool
    created_at: datetime


class HiddenJobMarketDashboardResponse(BaseModel):
    """Dashboard aggregate: signals + preferences + summary stats."""

    signals: list[CompanySignalSummaryResponse] = Field(default_factory=list)
    preferences: HiddenJobMarketPreferenceResponse | None = None
    total_signals: int = 0
    active_signals: int = 0
    matched_signals: int = 0
    dismissed_signals: int = 0
    total_opportunities: int = 0
    data_source: str = (
        "AI-generated signal intelligence based on public company data"
    )
    disclaimer: str = (
        "This signal analysis is AI-generated intelligence based on public data, "
        "not a guarantee of hiring intent. Company plans may change. "
        "Maximum confidence: 85%."
    )


class SignalComparisonResponse(BaseModel):
    """Side-by-side signal comparison."""

    signals: list[CompanySignalResponse] = Field(default_factory=list)
    comparison_summary: str | None = None
    recommended_signal_id: uuid.UUID | None = None
    data_source: str = (
        "AI-generated signal intelligence based on public company data"
    )
    disclaimer: str = (
        "This signal analysis is AI-generated intelligence based on public data, "
        "not a guarantee of hiring intent. Company plans may change. "
        "Maximum confidence: 85%."
    )


class OpportunityRadarResponse(BaseModel):
    """Aggregated opportunity landscape."""

    opportunities: list[HiddenOpportunityResponse] = Field(default_factory=list)
    total_opportunities: int = 0
    top_industries: list[str] = Field(default_factory=list)
    avg_probability: float = 0.0
    data_source: str = (
        "AI-generated signal intelligence based on public company data"
    )
    disclaimer: str = (
        "This signal analysis is AI-generated intelligence based on public data, "
        "not a guarantee of hiring intent. Company plans may change. "
        "Maximum confidence: 85%."
    )


# ── Request Schemas ────────────────────────────────────────────


class ScanCompanyRequest(BaseModel):
    """Scan a specific company for growth signals."""

    company_name: str = Field(
        ..., min_length=1, max_length=255,
        description="Target company name to scan for signals.",
    )
    industry: str | None = Field(
        None, max_length=100,
        description="Industry context for better signal detection.",
    )
    focus_signal_types: list[str] | None = Field(
        None,
        description="Optional filter: signal types to look for.",
    )


class ScanIndustryRequest(BaseModel):
    """Scan an industry for growth signals."""

    industry: str = Field(
        ..., min_length=1, max_length=100,
        description="Target industry to scan.",
    )
    region: str | None = Field(
        None, max_length=100,
        description="Geographic region for focused scanning.",
    )
    max_companies: int = Field(
        5, ge=1, le=20,
        description="Maximum companies to scan.",
    )


class GenerateOutreachRequest(BaseModel):
    """Generate outreach template for a specific signal."""

    template_type: str = Field(
        "introduction",
        description="Type: introduction, referral_request, informational_interview, direct_application.",
    )
    tone: str = Field(
        "professional",
        description="Tone: professional, casual, enthusiastic.",
    )
    custom_notes: str | None = Field(
        None, max_length=500,
        description="Optional user notes to personalize further.",
    )


class HiddenJobMarketPreferenceUpdateRequest(BaseModel):
    """Update user monitoring preferences."""

    min_signal_strength: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Minimum signal strength threshold.",
    )
    enabled_signal_types: list[str] | None = Field(
        None,
        description="Signal types to monitor.",
    )
    max_outreach_per_week: int | None = Field(
        None, ge=0, le=50,
        description="Max outreach messages per week.",
    )
    auto_generate_outreach: bool | None = Field(
        None,
        description="Auto-generate outreach when signals are matched.",
    )
    notification_enabled: bool | None = Field(
        None,
        description="Enable or disable signal notifications.",
    )


class SignalCompareRequest(BaseModel):
    """Compare multiple signals side-by-side."""

    signal_ids: list[uuid.UUID] = Field(
        ..., min_length=2, max_length=5,
        description="Signal IDs to compare (2-5 required).",
    )


class DismissSignalRequest(BaseModel):
    """Dismiss or action a signal."""

    reason: str | None = Field(
        None, max_length=500,
        description="Optional reason for dismissal.",
    )
    action_taken: str = Field(
        "dismissed",
        description="Action: dismissed or actioned.",
    )
