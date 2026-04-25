"""
PathForge — Interview Intelligence™ Schemas
=============================================
Request/response Pydantic schemas for the Interview Intelligence API.

Request schemas validate user input with constraints.
Response schemas provide full transparency (data_source, disclaimer).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ─────────────────────────────────────────


class CompanyInsightResponse(BaseModel):
    """A single company insight (format, culture, salary, etc.)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insight_type: str
    title: str
    content: dict[str, Any] | None = None
    summary: str | None = None
    source: str | None = None
    confidence: float


class InterviewQuestionResponse(BaseModel):
    """A predicted interview question with suggested answer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    question_text: str
    suggested_answer: str | None = None
    answer_strategy: str | None = None
    frequency_weight: float
    difficulty_level: str | None = None
    order_index: int


class STARExampleResponse(BaseModel):
    """A Career DNA–mapped STAR response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID | None = None
    situation: str
    task: str
    action: str
    result: str
    career_dna_dimension: str | None = None
    source_experience: str | None = None
    relevance_score: float
    order_index: int


class InterviewPrepResponse(BaseModel):
    """Full interview prep detail with all insights, questions, and STAR examples."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    company_name: str
    target_role: str
    status: str
    prep_depth: str
    confidence_score: float
    culture_alignment_score: float | None = None
    interview_format: str | None = None
    company_brief: str | None = None
    data_source: str
    disclaimer: str
    computed_at: datetime
    insights: list[CompanyInsightResponse] = Field(default_factory=list)
    questions: list[InterviewQuestionResponse] = Field(default_factory=list)
    star_examples: list[STARExampleResponse] = Field(default_factory=list)


class InterviewPrepSummaryResponse(BaseModel):
    """Lightweight prep card for list views and dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    target_role: str
    status: str
    confidence_score: float
    culture_alignment_score: float | None = None
    prep_depth: str
    data_source: str
    disclaimer: str
    computed_at: datetime


class NegotiationScriptResponse(BaseModel):
    """Salary negotiation strategy with data-backed scripts."""

    interview_prep_id: uuid.UUID
    company_name: str
    target_role: str
    salary_range_min: float | None = None
    salary_range_max: float | None = None
    salary_range_median: float | None = None
    currency: str = "EUR"
    opening_script: str
    counteroffer_script: str
    fallback_script: str
    key_arguments: list[str] = Field(default_factory=list)
    skill_premiums: dict[str, float] = Field(default_factory=dict)
    market_position_summary: str | None = None
    data_source: str = "AI-generated negotiation strategy based on Salary Intelligence Engine™ data"
    disclaimer: str = (
        "These negotiation scripts are AI-generated suggestions, not guarantees. "
        "Actual salary offers depend on the employer, market conditions, and negotiation dynamics. "
        "Use as guidance, not as a rigid script."
    )


class InterviewPreferenceResponse(BaseModel):
    """User preferences for the interview intelligence module."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    career_dna_id: uuid.UUID
    default_prep_depth: str | None = None
    max_saved_preps: int
    include_salary_negotiation: bool
    notification_enabled: bool


class InterviewDashboardResponse(BaseModel):
    """Dashboard: all preps + preferences + summary stats."""

    preps: list[InterviewPrepSummaryResponse] = Field(default_factory=list)
    preferences: InterviewPreferenceResponse | None = None
    total_preps: int = 0
    company_counts: dict[str, int] = Field(default_factory=dict)


class InterviewPrepComparisonResponse(BaseModel):
    """Side-by-side comparison of multiple interview preps."""

    model_config = ConfigDict(from_attributes=True)

    preps: list[InterviewPrepResponse]
    ranking: list[uuid.UUID] = Field(
        default_factory=list,
        description="Prep IDs ranked by composite readiness score",
    )
    comparison_summary: str | None = None
    data_source: str = "AI-generated comparison based on Career DNA and company intelligence"
    disclaimer: str = (
        "This comparison is an AI-generated analysis, not a guarantee. "
        "Interview readiness depends on preparation, company dynamics, "
        "and factors beyond prediction."
    )


# ── Request Schemas ──────────────────────────────────────────


class InterviewPrepRequest(BaseModel):
    """Create a new interview preparation session."""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company name to prepare for",
    )
    target_role: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target role at the company",
    )
    prep_depth: Literal["quick", "standard", "comprehensive"] | None = Field(
        None,
        description="Preparation depth: quick, standard, or comprehensive",
    )


class GenerateQuestionsRequest(BaseModel):
    """Request to generate interview questions for an existing prep."""

    category_filter: str | None = Field(
        None,
        max_length=30,
        description="Optional category filter: behavioral, technical, situational, culture_fit, salary",
    )
    max_questions: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum number of questions to generate (1-50)",
    )


class GenerateSTARExamplesRequest(BaseModel):
    """Request to generate STAR examples for an existing prep."""

    question_ids: list[uuid.UUID] | None = Field(
        None,
        max_length=20,
        description="Optional list of question IDs to generate STAR examples for",
    )
    max_examples: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Maximum number of STAR examples to generate (1-30)",
    )


class GenerateNegotiationScriptRequest(BaseModel):
    """Request to generate salary negotiation scripts for an existing prep."""

    target_salary: float | None = Field(
        None,
        gt=0,
        description="Optional target salary to anchor negotiation strategy",
    )
    currency: str = Field(
        default="EUR",
        max_length=10,
        description="Currency code (default: EUR)",
    )


class InterviewPreferenceUpdateRequest(BaseModel):
    """Partial update for interview preferences."""

    default_prep_depth: str | None = None
    max_saved_preps: int | None = Field(None, ge=1, le=100)
    include_salary_negotiation: bool | None = None
    notification_enabled: bool | None = None


class InterviewPrepCompareRequest(BaseModel):
    """Request to compare multiple saved interview preps."""

    prep_ids: list[uuid.UUID] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2-5 prep IDs to compare side-by-side",
    )
