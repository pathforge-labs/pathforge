"""Pydantic schemas for the AI Usage Summary endpoint (T4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EngineUsageResponse(BaseModel):
    """Per-engine usage row."""

    model_config = ConfigDict(from_attributes=True)

    engine: str = Field(
        ...,
        description=(
            "Engine principal name as recorded on each AITransparencyRecord (e.g. 'career_dna')."
        ),
    )
    calls: int = Field(..., ge=0, description="Number of completed AI calls in the period.")
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    cost_eur_cents: int = Field(
        ...,
        ge=0,
        description=(
            "Estimated EUR cost in cents (integer to avoid float drift). "
            "0 when the model is not in the price table — see "
            "`has_unpriced_models` on the parent summary."
        ),
    )
    avg_latency_ms: int = Field(..., ge=0)
    last_call_at: datetime | None = Field(
        None, description="UTC timestamp of the most recent call."
    )


class UsageSummaryResponse(BaseModel):
    """Aggregated AI usage for the current user × period."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    period_label: str = Field(..., description="e.g. 'current_month'.")
    period_start: datetime
    period_end: datetime
    total_calls: int = Field(..., ge=0)
    total_prompt_tokens: int = Field(..., ge=0)
    total_completion_tokens: int = Field(..., ge=0)
    total_cost_eur_cents: int = Field(
        ...,
        ge=0,
        description=(
            "Estimated EUR cost in cents across all engines. Free tier "
            "should display the call counts; premium tier should "
            "display this. The same response carries both fields per "
            "the Transparent AI Accounting decision (sprint plan §12 "
            "default #4 = dual-display)."
        ),
    )
    has_unpriced_models: bool = Field(
        False,
        description=(
            "True when at least one record's model isn't in the "
            "server-side price table; the UI should append "
            "'cost estimate excludes some calls' messaging."
        ),
    )
    engines: list[EngineUsageResponse]
