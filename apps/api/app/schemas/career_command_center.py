"""
PathForge — Career Command Center™ Schemas
============================================
Pydantic request/response schemas for the Career Command Center API.

Response Schemas (6):
    EngineStatusResponse               — Single engine heartbeat + score
    CareerSnapshotResponse             — Full snapshot with engine map
    CareerHealthSummaryResponse        — Lightweight health check
    CommandCenterPreferenceResponse    — Display preferences
    EngineDetailResponse               — Engine drill-down
    DashboardResponse                  — Complete dashboard aggregate

Request Schemas (1):
    CommandCenterPreferenceUpdate      — Update display preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class EngineStatusResponse(BaseModel):
    """Engine Heartbeat™ — single engine status in the dashboard."""

    engine_name: str
    display_name: str
    heartbeat: str = Field(
        ...,
        description="Freshness: active | stale | dormant | never_run",
    )
    score: float | None = Field(
        None, ge=0.0, le=100.0,
        description="Engine's native score (0-100), null if never run.",
    )
    last_updated: datetime | None = None
    trend: str | None = Field(
        None,
        description="improving | stable | declining | null",
    )
    summary: str | None = Field(
        None,
        description="Brief human-readable status summary.",
    )


class CareerSnapshotResponse(BaseModel):
    """Career Vitals™ — full snapshot with all engine statuses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    career_dna_id: uuid.UUID
    health_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Career Vitals™ composite health score (0-100).",
    )
    health_band: str = Field(
        ...,
        description="thriving | healthy | attention | at_risk | critical",
    )
    engine_statuses: dict[str, object] | None = None
    strengths: dict[str, object] | None = None
    attention_areas: dict[str, object] | None = None
    trend_direction: str
    data_source: str
    disclaimer: str
    created_at: datetime
    updated_at: datetime


class CareerHealthSummaryResponse(BaseModel):
    """Lightweight career health check — score + band + trend only."""

    health_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Career Vitals™ composite health score (0-100).",
    )
    health_band: str
    trend_direction: str
    engines_active: int = Field(
        ..., ge=0,
        description="Number of engines with active heartbeats.",
    )
    engines_total: int = Field(
        12,
        description="Total number of intelligence engines.",
    )
    top_strength: str | None = None
    top_attention: str | None = None
    data_source: str = "Career Vitals™ — 12-engine composite health score"
    disclaimer: str = (
        "Career Health Score is an AI-generated composite metric "
        "derived from 12 intelligence engines."
    )


class CommandCenterPreferenceResponse(BaseModel):
    """User display preferences for Career Command Center."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    pinned_engines: list[str] | None = None
    hidden_engines: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class EngineDetailResponse(BaseModel):
    """Engine drill-down — detailed status for a single engine."""

    engine_name: str
    display_name: str
    heartbeat: str
    score: float | None = None
    last_updated: datetime | None = None
    record_count: int = 0
    recent_records: list[dict[str, object]] = Field(default_factory=list)
    data_source: str = ""
    disclaimer: str = ""


class DashboardResponse(BaseModel):
    """Complete Career Command Center dashboard."""

    snapshot: CareerSnapshotResponse | None = None
    health_summary: CareerHealthSummaryResponse
    engine_statuses: list[EngineStatusResponse] = Field(
        default_factory=list,
    )
    preferences: CommandCenterPreferenceResponse | None = None
    data_source: str = "Career Vitals™ — Unified Career Command Center"
    disclaimer: str = (
        "The Career Command Center aggregates data from 12 AI "
        "intelligence engines. All scores are AI-generated and "
        "should be used alongside your own judgment."
    )


# ── Request Schemas ────────────────────────────────────────────


class CommandCenterPreferenceUpdate(BaseModel):
    """Update Career Command Center display preferences."""

    pinned_engines: list[str] | None = Field(
        None, max_length=12,
        description="Engines to pin (show first). Max 12.",
    )
    hidden_engines: list[str] | None = Field(
        None, max_length=11,
        description="Engines to hide. Max 11 (at least 1 must remain).",
    )
