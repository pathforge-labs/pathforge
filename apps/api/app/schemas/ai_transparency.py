"""
PathForge — AI Transparency Schemas
=====================================
Pydantic response models for the AI Trust Layer™ user-facing API.

These schemas define the contract between PathForge's backend and
frontend for AI decision transparency and system health reporting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AIAnalysisTransparencyResponse(BaseModel):
    """Single AI analysis transparency record for user consumption."""

    analysis_id: str = Field(description="Unique analysis identifier")
    analysis_type: str = Field(
        description="Type of analysis (e.g., 'career_dna.hidden_skills')",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Algorithmic confidence score (0.0-0.95, never 100%)",
    )
    confidence_label: str = Field(
        description="Human-readable confidence level: High, Medium, or Low",
    )
    model_tier: str = Field(
        description="AI model tier used: primary, fast, or deep",
    )
    tokens_used: int = Field(
        ge=0,
        description="Total tokens consumed by this analysis",
    )
    latency_ms: int = Field(
        ge=0,
        description="Analysis response time in milliseconds",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Data sources that fed this analysis",
    )
    timestamp: str = Field(description="ISO 8601 analysis timestamp")


class RecentAnalysesResponse(BaseModel):
    """Paginated list of recent AI analyses for a user."""

    analyses: list[AIAnalysisTransparencyResponse] = Field(
        default_factory=list,
    )
    total_count: int = Field(ge=0, description="Total records returned")
    user_id: str = Field(description="Authenticated user ID")


class AIHealthResponse(BaseModel):
    """Public AI system health dashboard.

    No authentication required — this is a trust signal showing
    PathForge is transparent about AI system reliability.
    """

    system_status: str = Field(
        description="Overall status: operational, degraded, or unavailable",
    )
    total_analyses: int = Field(
        ge=0,
        description="Total analyses processed since startup",
    )
    analyses_in_memory: int = Field(
        ge=0,
        description="Analyses currently in the transparency log",
    )
    success_rate: float = Field(
        ge=0.0,
        le=100.0,
        description="AI analysis success rate percentage",
    )
    avg_latency_ms: float = Field(
        ge=0.0,
        description="Average analysis latency in milliseconds",
    )
    uptime_seconds: float = Field(
        ge=0.0,
        description="Seconds since AI engine initialization",
    )
    last_analysis_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of most recent analysis",
    )
    active_users: int = Field(
        ge=0,
        description="Number of users with recorded analyses",
    )
    pending_persistence_tasks: int = Field(
        ge=0,
        default=0,
        description="Number of DB write tasks currently in-flight",
    )
    persistence_failures: int = Field(
        ge=0,
        default=0,
        description="Total DB persistence failures since startup",
    )
