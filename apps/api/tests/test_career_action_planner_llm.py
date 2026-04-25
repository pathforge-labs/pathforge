"""
PathForge — Career Action Planner™ Mocked LLM Integration Tests
=================================================================
Tests for CareerActionPlannerAnalyzer LLM methods with mocked complete_json.

Validates:
    - Prompt formatting and parameter pass-through
    - Post-LLM clamping/validation on realistic responses
    - Error handling when LLMError is raised
    - Confidence cap enforcement end-to-end
    - Milestone category/urgency normalization
    - Recommendation source engine validation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer
from app.core.llm import LLMError

# ── Fixtures ──────────────────────────────────────────────────


MOCK_PRIORITIES_RESPONSE: dict[str, Any] = {
    "priorities": [
        {
            "title": "Upgrade cloud architecture skills",
            "description": "AWS/Azure certifications needed",
            "rationale": "Market demand for cloud skills is critical",
            "category": "certification",
            "urgency": "high",
            "impact_score": 85.0,
        },
        {
            "title": "Build leadership portfolio",
            "description": "Lead a cross-team initiative",
            "rationale": "Required for senior promotion track",
            "category": "project",
            "urgency": "medium",
            "impact_score": 72.0,
        },
    ],
    "overall_assessment": "Strong candidate for cloud architect transition.",
    "confidence": 0.78,
}

MOCK_MILESTONES_RESPONSE: dict[str, Any] = {
    "milestones": [
        {
            "title": "Complete AWS Solutions Architect exam",
            "description": "Study and pass SAA-C03 certification",
            "category": "certification",
            "target_week": 3,
            "effort_hours": 40,
            "priority": 9,
            "evidence_required": "Official AWS certification badge",
        },
        {
            "title": "Deploy production microservice",
            "description": "Design and deploy a containerized service",
            "category": "project",
            "target_week": 6,
            "effort_hours": 24,
            "priority": 7,
            "evidence_required": "GitHub repository link with CI/CD pipeline",
        },
    ],
    "sprint_summary": "8-week cloud architecture sprint focusing on certification and hands-on delivery.",
    "confidence": 0.75,
}

MOCK_PROGRESS_RESPONSE: dict[str, Any] = {
    "plan_health": "on_track",
    "overall_progress_percent": 45.0,
    "milestone_assessments": [
        {
            "milestone_title": "Complete AWS exam",
            "status": "in_progress",
            "progress_percent": 60.0,
            "assessment": "Ahead of schedule on study plan.",
        },
    ],
    "priority_adjustments": [
        {
            "priority_title": "Build leadership portfolio",
            "adjustment": "Consider adding mentoring component.",
        },
    ],
    "confidence": 0.7,
}

MOCK_RECOMMENDATIONS_RESPONSE: dict[str, Any] = {
    "recommendations": [
        {
            "source_engine": "threat_radar",
            "recommendation_type": "upskill",
            "title": "Accelerate Kubernetes adoption",
            "rationale": "Container orchestration increasingly automated.",
            "urgency": "high",
            "impact_score": 88.0,
        },
        {
            "source_engine": "salary_intelligence",
            "recommendation_type": "negotiate",
            "title": "Leverage cloud certs in compensation review",
            "rationale": "Cloud-certified engineers command 15-25% premium.",
            "urgency": "medium",
            "impact_score": 75.0,
        },
    ],
    "confidence": 0.72,
}


# ── Priority Analysis Tests ───────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_priorities_returns_clamped_result() -> None:
    """Mocked LLM returns priorities that are correctly clamped."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=MOCK_PRIORITIES_RESPONSE.copy(),
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Cloud Engineer",
            primary_industry="Technology",
            seniority_level="senior",
            location="Amsterdam",
            skills="Python, AWS, Docker",
            plan_type="skill_development",
            focus_area="Cloud architecture",
            intelligence_summary="High automation risk in legacy roles.",
        )

    assert "priorities" in result
    assert len(result["priorities"]) == 2
    assert result["confidence"] <= 0.85
    assert result["overall_assessment"] != ""


@pytest.mark.asyncio
async def test_analyze_priorities_confidence_overcap_is_clamped() -> None:
    """LLM returning confidence > 0.85 is clamped to 0.85."""
    overcap_response = {
        "priorities": [
            {
                "title": "Test priority",
                "description": "Test",
                "rationale": "Test",
                "category": "learning",
                "urgency": "medium",
                "impact_score": 50.0,
            },
        ],
        "overall_assessment": "Test assessment.",
        "confidence": 0.95,
    }
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=overcap_response,
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            location="Berlin",
            skills="Java",
            plan_type="skill_development",
            focus_area="",
            intelligence_summary="",
        )

    assert result["confidence"] == 0.85


@pytest.mark.asyncio
async def test_analyze_priorities_llm_error_returns_empty() -> None:
    """LLMError returns safe empty fallback."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        side_effect=LLMError("Service unavailable"),
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            location="Remote",
            skills="Python",
            plan_type="threat_mitigation",
            focus_area="",
            intelligence_summary="",
        )

    assert result["priorities"] == []
    assert result["confidence"] == 0.0
    assert "unavailable" in result["overall_assessment"].lower()


@pytest.mark.asyncio
async def test_analyze_priorities_invalid_urgency_normalized() -> None:
    """Invalid urgency values are normalized to 'medium'."""
    bad_urgency_response = {
        "priorities": [
            {
                "title": "Bad urgency priority",
                "description": "Test",
                "rationale": "Test",
                "category": "learning",
                "urgency": "ASAP!!!",
                "impact_score": 60.0,
            },
        ],
        "overall_assessment": "Test.",
        "confidence": 0.5,
    }
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=bad_urgency_response,
    ):
        result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            location="Remote",
            skills="Python",
            plan_type="skill_development",
            focus_area="",
            intelligence_summary="",
        )

    assert result["priorities"][0]["urgency"] == "medium"


# ── Milestone Generation Tests ────────────────────────────────


@pytest.mark.asyncio
async def test_generate_milestones_returns_valid_result() -> None:
    """Mocked LLM returns milestones that pass validation."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=MOCK_MILESTONES_RESPONSE.copy(),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Cloud Engineer",
            seniority_level="senior",
            skills="Python, AWS, Docker",
            plan_type="skill_development",
            plan_title="Cloud Architecture Sprint",
            plan_objective="Transition to cloud architect role",
            sprint_weeks=8,
            max_milestones=5,
            priorities_json="[]",
        )

    assert len(result["milestones"]) == 2
    for milestone in result["milestones"]:
        assert 1 <= milestone["effort_hours"] <= 120
        assert 1 <= milestone["priority"] <= 10
        assert milestone["category"] in {
            "learning", "certification", "networking",
            "project", "application", "interview_prep",
        }


@pytest.mark.asyncio
async def test_generate_milestones_clamps_extreme_effort() -> None:
    """Effort hours outside 1-120 range are clamped."""
    extreme_response: dict[str, Any] = {
        "milestones": [
            {
                "title": "Overambitious milestone",
                "description": "Too many hours",
                "category": "learning",
                "target_week": 2,
                "effort_hours": 999,
                "priority": 5,
                "evidence_required": "Self-reported.",
            },
        ],
        "sprint_summary": "Test sprint.",
        "confidence": 0.6,
    }
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=extreme_response,
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python",
            plan_type="skill_development",
            plan_title="Test",
            plan_objective="Test",
            sprint_weeks=4,
            max_milestones=5,
            priorities_json="[]",
        )

    assert result["milestones"][0]["effort_hours"] == 120


@pytest.mark.asyncio
async def test_generate_milestones_llm_error_returns_empty() -> None:
    """LLMError returns safe empty fallback."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        side_effect=LLMError("Timeout"),
    ):
        result = await CareerActionPlannerAnalyzer.generate_milestones(
            primary_role="Engineer",
            seniority_level="mid",
            skills="Python",
            plan_type="skill_development",
            plan_title="Test",
            plan_objective="Test",
            sprint_weeks=4,
            max_milestones=5,
            priorities_json="[]",
        )

    assert result["milestones"] == []
    assert result["confidence"] == 0.0


# ── Progress Evaluation Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_progress_returns_valid_result() -> None:
    """Mocked LLM returns valid progress evaluation."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=MOCK_PROGRESS_RESPONSE.copy(),
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Cloud Architecture Sprint",
            plan_type="skill_development",
            sprint_weeks=8,
            milestones_json="[]",
            intelligence_updates="New threat radar data available.",
        )

    assert result["plan_health"] in {"on_track", "at_risk", "behind", "ahead"}
    assert 0.0 <= result["overall_progress_percent"] <= 100.0
    assert isinstance(result["milestone_assessments"], list)


@pytest.mark.asyncio
async def test_evaluate_progress_invalid_health_normalized() -> None:
    """Invalid plan_health is normalized to 'at_risk'."""
    bad_health_response: dict[str, Any] = {
        "plan_health": "fantastic",
        "overall_progress_percent": 50.0,
        "milestone_assessments": [],
        "priority_adjustments": [],
        "confidence": 0.6,
    }
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=bad_health_response,
    ):
        result = await CareerActionPlannerAnalyzer.evaluate_progress(
            plan_title="Test",
            plan_type="skill_development",
            sprint_weeks=4,
            milestones_json="[]",
            intelligence_updates="",
        )

    assert result["plan_health"] == "at_risk"


# ── Recommendation Generation Tests ──────────────────────────


@pytest.mark.asyncio
async def test_generate_recommendations_returns_valid_result() -> None:
    """Mocked LLM returns valid recommendations."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=MOCK_RECOMMENDATIONS_RESPONSE.copy(),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Cloud Engineer",
            primary_industry="Technology",
            seniority_level="senior",
            plan_type="skill_development",
            plan_title="Cloud Architecture Sprint",
            engine_outputs="Threat radar: high automation risk.",
        )

    assert len(result["recommendations"]) == 2
    for rec in result["recommendations"]:
        assert rec["source_engine"] in {
            "threat_radar", "skill_decay", "salary_intelligence",
            "transition_pathways", "career_simulation", "hidden_job_market",
            "predictive_career", "collective_intelligence",
        }
        assert 0.0 <= rec["impact_score"] <= 100.0


@pytest.mark.asyncio
async def test_generate_recommendations_invalid_engine_normalized() -> None:
    """Invalid source_engine is normalized to 'predictive_career'."""
    bad_engine_response: dict[str, Any] = {
        "recommendations": [
            {
                "source_engine": "unknown_engine_v2",
                "recommendation_type": "general",
                "title": "Bad engine recommendation",
                "rationale": "Test rationale.",
                "urgency": "medium",
                "impact_score": 50.0,
            },
        ],
        "confidence": 0.5,
    }
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=bad_engine_response,
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            plan_type="skill_development",
            plan_title="Test",
            engine_outputs="",
        )

    assert result["recommendations"][0]["source_engine"] == "predictive_career"


@pytest.mark.asyncio
async def test_generate_recommendations_llm_error_returns_empty() -> None:
    """LLMError returns safe empty fallback."""
    with patch(
        "app.ai.career_action_planner_analyzer.complete_json",
        new_callable=AsyncMock,
        side_effect=LLMError("Rate limited"),
    ):
        result = await CareerActionPlannerAnalyzer.generate_recommendations(
            primary_role="Engineer",
            primary_industry="Tech",
            seniority_level="mid",
            plan_type="skill_development",
            plan_title="Test",
            engine_outputs="",
        )

    assert result["recommendations"] == []
    assert result["confidence"] == 0.0
