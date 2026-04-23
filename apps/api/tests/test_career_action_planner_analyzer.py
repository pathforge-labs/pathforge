"""Unit tests for CareerActionPlannerAnalyzer — direct import, no API layer."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.career_action_planner_analyzer import (
    MAX_IMPACT_SCORE,
    MAX_PLAN_CONFIDENCE,
    VALID_MILESTONE_CATEGORIES,
    VALID_SOURCE_ENGINES,
    VALID_URGENCY_LEVELS,
    CareerActionPlannerAnalyzer,
    _clamp_confidence_field,
    _clamp_milestones,
    _clamp_priorities,
    _clamp_progress_evaluation,
    _clamp_recommendations,
)
from app.core.llm import LLMError

# ── helpers ───────────────────────────────────────────────────────────────────

def _sanitize_passthrough(text, *, max_length, context):
    return text[:max_length], {}


def _make_priority(**kwargs):
    base = {
        "title": "Learn Python",
        "description": "Master Python basics",
        "rationale": "High demand skill",
        "urgency": "high",
        "category": "learning",
        "impact_score": 80.0,
    }
    base.update(kwargs)
    return base


def _make_milestone(**kwargs):
    base = {
        "title": "Complete course",
        "description": "Finish online course",
        "category": "learning",
        "effort_hours": 20,
        "priority": 3,
        "evidence_required": "Certificate of completion",
    }
    base.update(kwargs)
    return base


def _make_recommendation(**kwargs):
    base = {
        "title": "Upskill in ML",
        "rationale": "High market demand",
        "recommendation_type": "skill",
        "source_engine": "skill_decay",
        "urgency": "high",
        "impact_score": 75.0,
    }
    base.update(kwargs)
    return base


# ── constants ─────────────────────────────────────────────────────────────────

def test_max_plan_confidence():
    assert MAX_PLAN_CONFIDENCE == 0.85


def test_max_impact_score():
    assert MAX_IMPACT_SCORE == 100.0


def test_valid_urgency_levels():
    assert "critical" in VALID_URGENCY_LEVELS
    assert "high" in VALID_URGENCY_LEVELS
    assert "medium" in VALID_URGENCY_LEVELS
    assert "low" in VALID_URGENCY_LEVELS


def test_valid_milestone_categories():
    for cat in ("learning", "certification", "networking", "project",
                "application", "interview_prep"):
        assert cat in VALID_MILESTONE_CATEGORIES


def test_valid_source_engines():
    for engine in ("threat_radar", "skill_decay", "salary_intelligence",
                   "transition_pathways", "career_simulation",
                   "hidden_job_market", "predictive_career",
                   "collective_intelligence"):
        assert engine in VALID_SOURCE_ENGINES


# ── clamp_confidence (static method) ─────────────────────────────────────────

def test_clamp_confidence_normal():
    assert CareerActionPlannerAnalyzer.clamp_confidence(0.5) == 0.5


def test_clamp_confidence_at_cap():
    assert CareerActionPlannerAnalyzer.clamp_confidence(0.85) == 0.85


def test_clamp_confidence_above_cap():
    assert CareerActionPlannerAnalyzer.clamp_confidence(1.0) == 0.85


def test_clamp_confidence_below_zero():
    assert CareerActionPlannerAnalyzer.clamp_confidence(-0.1) == 0.0


def test_clamp_confidence_non_numeric():
    assert CareerActionPlannerAnalyzer.clamp_confidence("high") == 0.0  # type: ignore[arg-type]


def test_clamp_confidence_integer():
    assert CareerActionPlannerAnalyzer.clamp_confidence(0) == 0.0


# ── clamp_impact_score (static method) ───────────────────────────────────────

def test_clamp_impact_score_normal():
    assert CareerActionPlannerAnalyzer.clamp_impact_score(75.0) == 75.0


def test_clamp_impact_score_at_max():
    assert CareerActionPlannerAnalyzer.clamp_impact_score(100.0) == 100.0


def test_clamp_impact_score_above_max():
    assert CareerActionPlannerAnalyzer.clamp_impact_score(150.0) == 100.0


def test_clamp_impact_score_below_zero():
    assert CareerActionPlannerAnalyzer.clamp_impact_score(-10.0) == 0.0


def test_clamp_impact_score_non_numeric():
    assert CareerActionPlannerAnalyzer.clamp_impact_score("high") == 0.0  # type: ignore[arg-type]


def test_clamp_impact_score_integer():
    assert CareerActionPlannerAnalyzer.clamp_impact_score(50) == 50.0


# ── build_priority_context (static method) ────────────────────────────────────

def test_build_priority_context_all_fields():
    ctx = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role="Data Scientist",
        primary_industry="Finance",
        seniority_level="senior",
        location="London",
        skills=["Python", "SQL", "ML"],
    )
    assert ctx["primary_role"] == "Data Scientist"
    assert ctx["primary_industry"] == "Finance"
    assert ctx["seniority_level"] == "senior"
    assert ctx["location"] == "London"
    assert "Python" in ctx["skills"]


def test_build_priority_context_none_fields():
    ctx = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role=None,
        primary_industry=None,
        seniority_level=None,
        location=None,
        skills=[],
    )
    assert ctx["primary_role"] == "Not specified"
    assert ctx["primary_industry"] == "Not specified"
    assert ctx["seniority_level"] == "mid"
    assert ctx["location"] == "Not specified"
    assert ctx["skills"] == "No skills listed"


def test_build_priority_context_skills_truncated_at_20():
    skills = [f"Skill{i}" for i in range(25)]
    ctx = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role="Engineer",
        primary_industry="Tech",
        seniority_level="mid",
        location="Berlin",
        skills=skills,
    )
    parts = [s.strip() for s in ctx["skills"].split(",")]
    assert len(parts) == 20


# ── validate_milestone_timeline (static method) ───────────────────────────────

def test_validate_milestone_timeline_none():
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=None, sprint_weeks=4,
    )
    assert result is None


def test_validate_milestone_timeline_past_date():
    past = date.today() - timedelta(days=10)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=past, sprint_weeks=4,
    )
    assert result == date.today() + timedelta(days=7)


def test_validate_milestone_timeline_future_within_range():
    future = date.today() + timedelta(weeks=3)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=future, sprint_weeks=4,
    )
    assert result == future


def test_validate_milestone_timeline_future_beyond_range():
    future = date.today() + timedelta(weeks=20)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=future, sprint_weeks=4,
    )
    assert result == date.today() + timedelta(weeks=6)


def test_validate_milestone_timeline_zero_sprint_weeks():
    future = date.today() + timedelta(weeks=5)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=future, sprint_weeks=0,
    )
    assert result == date.today() + timedelta(weeks=3)


# ── _clamp_confidence_field ───────────────────────────────────────────────────

def test_clamp_confidence_field_normal():
    data: dict = {"confidence": 0.6}
    _clamp_confidence_field(data)
    assert data["confidence"] == 0.6


def test_clamp_confidence_field_above_cap():
    data: dict = {"confidence": 1.0}
    _clamp_confidence_field(data)
    assert data["confidence"] == MAX_PLAN_CONFIDENCE


def test_clamp_confidence_field_non_numeric():
    data: dict = {"confidence": "high"}
    _clamp_confidence_field(data)
    assert data["confidence"] == 0.0


def test_clamp_confidence_field_missing():
    data: dict = {}
    _clamp_confidence_field(data)
    assert data["confidence"] == 0.0


# ── _clamp_priorities ─────────────────────────────────────────────────────────

def test_clamp_priorities_valid():
    data = {
        "confidence": 0.7,
        "priorities": [_make_priority()],
        "overall_assessment": "Good profile.",
    }
    _clamp_priorities(data)
    assert len(data["priorities"]) == 1
    assert data["confidence"] == 0.7


def test_clamp_priorities_non_list():
    data = {"confidence": 0.5, "priorities": "not a list"}
    _clamp_priorities(data)
    assert data["priorities"] == []


def test_clamp_priorities_caps_at_5():
    data = {
        "confidence": 0.6,
        "priorities": [_make_priority(title=f"P{i}") for i in range(8)],
    }
    _clamp_priorities(data)
    assert len(data["priorities"]) == 5


def test_clamp_priorities_skips_non_dict():
    data = {"confidence": 0.5, "priorities": ["string", 42, _make_priority()]}
    _clamp_priorities(data)
    assert len(data["priorities"]) == 1


def test_clamp_priorities_invalid_urgency_defaults_to_medium():
    data = {"confidence": 0.5, "priorities": [_make_priority(urgency="extreme")]}
    _clamp_priorities(data)
    assert data["priorities"][0]["urgency"] == "medium"


def test_clamp_priorities_invalid_category_defaults_to_learning():
    data = {"confidence": 0.5, "priorities": [_make_priority(category="unknown")]}
    _clamp_priorities(data)
    assert data["priorities"][0]["category"] == "learning"


def test_clamp_priorities_impact_score_clamped():
    data = {"confidence": 0.5, "priorities": [_make_priority(impact_score=150.0)]}
    _clamp_priorities(data)
    assert data["priorities"][0]["impact_score"] == 100.0


def test_clamp_priorities_impact_score_negative():
    data = {"confidence": 0.5, "priorities": [_make_priority(impact_score=-5.0)]}
    _clamp_priorities(data)
    assert data["priorities"][0]["impact_score"] == 0.0


def test_clamp_priorities_impact_score_non_numeric():
    data = {"confidence": 0.5, "priorities": [_make_priority(impact_score="high")]}
    _clamp_priorities(data)
    assert data["priorities"][0]["impact_score"] == 50.0


def test_clamp_priorities_missing_title():
    p = _make_priority()
    del p["title"]
    data = {"confidence": 0.5, "priorities": [p]}
    _clamp_priorities(data)
    assert data["priorities"][0]["title"] == "Unnamed priority"


def test_clamp_priorities_missing_description():
    p = _make_priority()
    del p["description"]
    data = {"confidence": 0.5, "priorities": [p]}
    _clamp_priorities(data)
    assert data["priorities"][0]["description"] == "No description provided."


def test_clamp_priorities_missing_rationale():
    p = _make_priority()
    del p["rationale"]
    data = {"confidence": 0.5, "priorities": [p]}
    _clamp_priorities(data)
    assert data["priorities"][0]["rationale"] == "AI-generated priority."


def test_clamp_priorities_missing_overall_assessment():
    data = {"confidence": 0.5, "priorities": [_make_priority()]}
    _clamp_priorities(data)
    assert data["overall_assessment"] == "Assessment pending."


def test_clamp_priorities_existing_overall_assessment_preserved():
    data = {
        "confidence": 0.5,
        "priorities": [_make_priority()],
        "overall_assessment": "Strong profile.",
    }
    _clamp_priorities(data)
    assert data["overall_assessment"] == "Strong profile."


# ── _clamp_milestones ─────────────────────────────────────────────────────────

def test_clamp_milestones_valid():
    data = {
        "confidence": 0.7,
        "milestones": [_make_milestone()],
        "sprint_summary": "Good sprint plan.",
    }
    _clamp_milestones(data)
    assert len(data["milestones"]) == 1
    assert data["sprint_summary"] == "Good sprint plan."


def test_clamp_milestones_non_list():
    data = {"confidence": 0.5, "milestones": "not a list"}
    _clamp_milestones(data)
    assert data["milestones"] == []


def test_clamp_milestones_caps_at_max_milestones():
    data = {
        "confidence": 0.5,
        "milestones": [_make_milestone(title=f"M{i}") for i in range(8)],
    }
    _clamp_milestones(data, max_milestones=3)
    assert len(data["milestones"]) == 3


def test_clamp_milestones_skips_non_dict():
    data = {
        "confidence": 0.5,
        "milestones": ["string", 42, _make_milestone()],
    }
    _clamp_milestones(data)
    assert len(data["milestones"]) == 1


def test_clamp_milestones_invalid_category_defaults_to_learning():
    data = {"confidence": 0.5, "milestones": [_make_milestone(category="invalid")]}
    _clamp_milestones(data)
    assert data["milestones"][0]["category"] == "learning"


def test_clamp_milestones_effort_hours_too_high():
    data = {"confidence": 0.5, "milestones": [_make_milestone(effort_hours=200)]}
    _clamp_milestones(data)
    assert data["milestones"][0]["effort_hours"] == 120


def test_clamp_milestones_effort_hours_too_low():
    data = {"confidence": 0.5, "milestones": [_make_milestone(effort_hours=0)]}
    _clamp_milestones(data)
    assert data["milestones"][0]["effort_hours"] == 1


def test_clamp_milestones_effort_hours_non_numeric():
    data = {"confidence": 0.5, "milestones": [_make_milestone(effort_hours="many")]}
    _clamp_milestones(data)
    assert data["milestones"][0]["effort_hours"] == 8


def test_clamp_milestones_priority_too_high():
    data = {"confidence": 0.5, "milestones": [_make_milestone(priority=15)]}
    _clamp_milestones(data)
    assert data["milestones"][0]["priority"] == 10


def test_clamp_milestones_priority_too_low():
    data = {"confidence": 0.5, "milestones": [_make_milestone(priority=0)]}
    _clamp_milestones(data)
    assert data["milestones"][0]["priority"] == 1


def test_clamp_milestones_priority_non_numeric():
    data = {"confidence": 0.5, "milestones": [_make_milestone(priority="high")]}
    _clamp_milestones(data)
    assert data["milestones"][0]["priority"] == 5


def test_clamp_milestones_missing_title():
    m = _make_milestone()
    del m["title"]
    data = {"confidence": 0.5, "milestones": [m]}
    _clamp_milestones(data)
    assert data["milestones"][0]["title"] == "Unnamed milestone"


def test_clamp_milestones_missing_description():
    m = _make_milestone()
    del m["description"]
    data = {"confidence": 0.5, "milestones": [m]}
    _clamp_milestones(data)
    assert data["milestones"][0]["description"] == "No description provided."


def test_clamp_milestones_missing_evidence_required():
    m = _make_milestone()
    del m["evidence_required"]
    data = {"confidence": 0.5, "milestones": [m]}
    _clamp_milestones(data)
    assert "Self-reported" in data["milestones"][0]["evidence_required"]


def test_clamp_milestones_missing_sprint_summary():
    data = {"confidence": 0.5, "milestones": [_make_milestone()]}
    _clamp_milestones(data)
    assert data["sprint_summary"] == "Career sprint plan."


def test_clamp_milestones_default_max_is_5():
    data = {
        "confidence": 0.5,
        "milestones": [_make_milestone(title=f"M{i}") for i in range(7)],
    }
    _clamp_milestones(data)
    assert len(data["milestones"]) == 5


# ── _clamp_progress_evaluation ────────────────────────────────────────────────

def test_clamp_progress_evaluation_valid():
    data = {
        "confidence": 0.6,
        "plan_health": "on_track",
        "overall_progress_percent": 45.0,
        "milestone_assessments": [{"id": 1}],
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["plan_health"] == "on_track"
    assert data["overall_progress_percent"] == 45.0


def test_clamp_progress_evaluation_invalid_health():
    data = {
        "confidence": 0.5,
        "plan_health": "unknown_status",
        "overall_progress_percent": 50.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["plan_health"] == "at_risk"


def test_clamp_progress_evaluation_all_valid_health_values():
    for health in ("on_track", "at_risk", "behind", "ahead"):
        data = {"plan_health": health, "overall_progress_percent": 50.0,
                "milestone_assessments": [], "priority_adjustments": []}
        _clamp_progress_evaluation(data)
        assert data["plan_health"] == health


def test_clamp_progress_evaluation_progress_above_100():
    data = {
        "confidence": 0.5,
        "plan_health": "ahead",
        "overall_progress_percent": 150.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["overall_progress_percent"] == 100.0


def test_clamp_progress_evaluation_progress_negative():
    data = {
        "confidence": 0.5,
        "plan_health": "behind",
        "overall_progress_percent": -10.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["overall_progress_percent"] == 0.0


def test_clamp_progress_evaluation_progress_non_numeric():
    data = {
        "confidence": 0.5,
        "plan_health": "on_track",
        "overall_progress_percent": "fifty",
        "milestone_assessments": [],
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["overall_progress_percent"] == 0.0


def test_clamp_progress_evaluation_non_list_assessments():
    data = {
        "confidence": 0.5,
        "plan_health": "on_track",
        "overall_progress_percent": 50.0,
        "milestone_assessments": "not a list",
        "priority_adjustments": [],
    }
    _clamp_progress_evaluation(data)
    assert data["milestone_assessments"] == []


def test_clamp_progress_evaluation_non_list_adjustments():
    data = {
        "confidence": 0.5,
        "plan_health": "on_track",
        "overall_progress_percent": 50.0,
        "milestone_assessments": [],
        "priority_adjustments": "not a list",
    }
    _clamp_progress_evaluation(data)
    assert data["priority_adjustments"] == []


# ── _clamp_recommendations ────────────────────────────────────────────────────

def test_clamp_recommendations_valid():
    data = {
        "confidence": 0.7,
        "recommendations": [_make_recommendation()],
    }
    _clamp_recommendations(data)
    assert len(data["recommendations"]) == 1


def test_clamp_recommendations_non_list():
    data = {"confidence": 0.5, "recommendations": "not a list"}
    _clamp_recommendations(data)
    assert data["recommendations"] == []


def test_clamp_recommendations_caps_at_5():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(title=f"R{i}") for i in range(8)],
    }
    _clamp_recommendations(data)
    assert len(data["recommendations"]) == 5


def test_clamp_recommendations_skips_non_dict():
    data = {
        "confidence": 0.5,
        "recommendations": ["string", 42, _make_recommendation()],
    }
    _clamp_recommendations(data)
    assert len(data["recommendations"]) == 1


def test_clamp_recommendations_invalid_engine_defaults():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(source_engine="unknown_engine")],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["source_engine"] == "predictive_career"


def test_clamp_recommendations_empty_engine_defaults():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(source_engine="")],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["source_engine"] == "predictive_career"


def test_clamp_recommendations_invalid_urgency_defaults_to_medium():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(urgency="extreme")],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["urgency"] == "medium"


def test_clamp_recommendations_impact_score_above_100():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(impact_score=150.0)],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["impact_score"] == 100.0


def test_clamp_recommendations_impact_score_negative():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(impact_score=-5.0)],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["impact_score"] == 0.0


def test_clamp_recommendations_impact_score_non_numeric():
    data = {
        "confidence": 0.5,
        "recommendations": [_make_recommendation(impact_score="high")],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["impact_score"] == 50.0


def test_clamp_recommendations_missing_title():
    r = _make_recommendation()
    del r["title"]
    data = {"confidence": 0.5, "recommendations": [r]}
    _clamp_recommendations(data)
    assert data["recommendations"][0]["title"] == "Unnamed recommendation"


def test_clamp_recommendations_missing_rationale():
    r = _make_recommendation()
    del r["rationale"]
    data = {"confidence": 0.5, "recommendations": [r]}
    _clamp_recommendations(data)
    assert data["recommendations"][0]["rationale"] == "AI-generated recommendation."


def test_clamp_recommendations_missing_recommendation_type():
    r = _make_recommendation()
    del r["recommendation_type"]
    data = {"confidence": 0.5, "recommendations": [r]}
    _clamp_recommendations(data)
    assert data["recommendations"][0]["recommendation_type"] == "general"


def test_clamp_recommendations_all_valid_engines():
    for engine in VALID_SOURCE_ENGINES:
        data = {
            "confidence": 0.5,
            "recommendations": [_make_recommendation(source_engine=engine)],
        }
        _clamp_recommendations(data)
        assert data["recommendations"][0]["source_engine"] == engine


# ── LLM methods ───────────────────────────────────────────────────────────────

MODULE = "app.ai.career_action_planner_analyzer"


@pytest.mark.asyncio
async def test_analyze_career_priorities_success():
    llm_response = {
        "priorities": [_make_priority()],
        "overall_assessment": "Strong candidate.",
        "confidence": 0.75,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Software Engineer",
            primary_industry="Technology",
            seniority_level="senior",
            location="Berlin",
            skills="Python, SQL",
            plan_type="growth",
            focus_area="ML specialization",
            intelligence_summary="Strong demand for ML skills.",
        )

    assert len(result["priorities"]) == 1
    assert result["confidence"] == 0.75
    assert result["overall_assessment"] == "Strong candidate."


@pytest.mark.asyncio
async def test_analyze_career_priorities_clamps_confidence():
    llm_response = {
        "priorities": [_make_priority()],
        "overall_assessment": "Test.",
        "confidence": 1.0,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            location="London",
            skills="Python",
            plan_type="growth",
            focus_area="Cloud",
            intelligence_summary="",
        )

    assert result["confidence"] == MAX_PLAN_CONFIDENCE


@pytest.mark.asyncio
async def test_analyze_career_priorities_llm_error_fallback():
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock,
              side_effect=LLMError("timeout")),
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            location="Berlin",
            skills="Python",
            plan_type="growth",
            focus_area="General",
            intelligence_summary="",
        )

    assert result["priorities"] == []
    assert result["confidence"] == 0.0
    assert "unavailable" in result["overall_assessment"].lower()


@pytest.mark.asyncio
async def test_analyze_career_priorities_empty_role_defaults():
    llm_response = {"priorities": [], "overall_assessment": "N/A", "confidence": 0.5}
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response) as mock_llm,
    ):
        await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="",
            primary_industry="",
            seniority_level="",
            location="",
            skills="",
            plan_type="growth",
            focus_area="",
            intelligence_summary="",
        )

    call_kwargs = mock_llm.call_args
    assert call_kwargs is not None


@pytest.mark.asyncio
async def test_generate_milestones_success():
    llm_response = {
        "milestones": [_make_milestone()],
        "sprint_summary": "Good 4-week sprint.",
        "confidence": 0.70,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python, Docker",
            plan_type="growth",
            plan_title="Q2 Career Sprint",
            plan_objective="Become ML Engineer",
            sprint_weeks=4,
            max_milestones=5,
            priorities_json='[{"title": "Learn ML"}]',
        )

    assert len(result["milestones"]) == 1
    assert result["confidence"] == 0.70
    assert result["sprint_summary"] == "Good 4-week sprint."


@pytest.mark.asyncio
async def test_generate_milestones_clamps_confidence():
    llm_response = {
        "milestones": [_make_milestone()],
        "sprint_summary": "Sprint plan.",
        "confidence": 0.99,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python",
            plan_type="growth",
            plan_title="Sprint",
            plan_objective="Grow",
            sprint_weeks=4,
            max_milestones=5,
            priorities_json="[]",
        )

    assert result["confidence"] == MAX_PLAN_CONFIDENCE


@pytest.mark.asyncio
async def test_generate_milestones_llm_error_fallback():
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock,
              side_effect=LLMError("timeout")),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python",
            plan_type="growth",
            plan_title="Sprint",
            plan_objective="Grow",
            sprint_weeks=4,
            max_milestones=5,
            priorities_json="[]",
        )

    assert result["milestones"] == []
    assert result["confidence"] == 0.0
    assert "unavailable" in result["sprint_summary"].lower()


@pytest.mark.asyncio
async def test_generate_milestones_respects_max_milestones():
    llm_response = {
        "milestones": [_make_milestone(title=f"M{i}") for i in range(8)],
        "sprint_summary": "Big sprint.",
        "confidence": 0.6,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python",
            plan_type="growth",
            plan_title="Sprint",
            plan_objective="Grow",
            sprint_weeks=4,
            max_milestones=3,
            priorities_json="[]",
        )

    assert len(result["milestones"]) == 3


@pytest.mark.asyncio
async def test_evaluate_progress_success():
    llm_response = {
        "plan_health": "on_track",
        "overall_progress_percent": 60.0,
        "milestone_assessments": [{"id": 1, "status": "complete"}],
        "priority_adjustments": [],
        "confidence": 0.72,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Q2 Career Sprint",
            plan_type="growth",
            sprint_weeks=4,
            milestones_json='[{"title": "Complete course", "completed": true}]',
            intelligence_updates="Demand still high for ML.",
        )

    assert result["plan_health"] == "on_track"
    assert result["overall_progress_percent"] == 60.0
    assert result["confidence"] == 0.72


@pytest.mark.asyncio
async def test_evaluate_progress_clamps_confidence():
    llm_response = {
        "plan_health": "ahead",
        "overall_progress_percent": 80.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
        "confidence": 1.5,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Sprint",
            plan_type="growth",
            sprint_weeks=4,
            milestones_json="[]",
            intelligence_updates="",
        )

    assert result["confidence"] == MAX_PLAN_CONFIDENCE


@pytest.mark.asyncio
async def test_evaluate_progress_llm_error_fallback():
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock,
              side_effect=LLMError("timeout")),
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Sprint",
            plan_type="growth",
            sprint_weeks=4,
            milestones_json="[]",
            intelligence_updates="",
        )

    assert result["plan_health"] == "at_risk"
    assert result["overall_progress_percent"] == 0.0
    assert result["milestone_assessments"] == []
    assert result["priority_adjustments"] == []
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_evaluate_progress_clamps_invalid_health():
    llm_response = {
        "plan_health": "amazing",
        "overall_progress_percent": 50.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
        "confidence": 0.6,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Sprint",
            plan_type="growth",
            sprint_weeks=4,
            milestones_json="[]",
            intelligence_updates="",
        )

    assert result["plan_health"] == "at_risk"


@pytest.mark.asyncio
async def test_generate_recommendations_success():
    llm_response = {
        "recommendations": [_make_recommendation()],
        "confidence": 0.68,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Software Engineer",
            primary_industry="Technology",
            seniority_level="senior",
            plan_type="growth",
            plan_title="Q2 Career Sprint",
            engine_outputs='{"skill_decay": {"risk": "high"}}',
        )

    assert len(result["recommendations"]) == 1
    assert result["confidence"] == 0.68


@pytest.mark.asyncio
async def test_generate_recommendations_clamps_confidence():
    llm_response = {
        "recommendations": [_make_recommendation()],
        "confidence": 2.0,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            plan_type="growth",
            plan_title="Sprint",
            engine_outputs="{}",
        )

    assert result["confidence"] == MAX_PLAN_CONFIDENCE


@pytest.mark.asyncio
async def test_generate_recommendations_llm_error_fallback():
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock,
              side_effect=LLMError("timeout")),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            plan_type="growth",
            plan_title="Sprint",
            engine_outputs="{}",
        )

    assert result["recommendations"] == []
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_generate_recommendations_caps_at_5():
    llm_response = {
        "recommendations": [_make_recommendation(title=f"R{i}") for i in range(8)],
        "confidence": 0.6,
    }
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            plan_type="growth",
            plan_title="Sprint",
            engine_outputs="{}",
        )

    assert len(result["recommendations"]) == 5


@pytest.mark.asyncio
async def test_generate_recommendations_empty_role_defaults():
    llm_response = {"recommendations": [], "confidence": 0.5}
    with (
        patch(f"{MODULE}.sanitize_user_text", side_effect=_sanitize_passthrough),
        patch(f"{MODULE}.complete_json", new_callable=AsyncMock, return_value=llm_response) as mock_llm,
    ):
        await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="",
            primary_industry="",
            seniority_level="",
            plan_type="growth",
            plan_title="Sprint",
            engine_outputs="",
        )

    assert mock_llm.called
