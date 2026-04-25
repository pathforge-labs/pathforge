"""
PathForge — Career Action Planner™ Tests
==========================================
Test suite for:
    - Career Action Planner model creation (5 entities)
    - Static analyzer helpers (confidence, impact, timeline, context)
    - Clamping validators (priorities, milestones, progress, recommendations)
    - Schema validation (request + response)
    - API endpoint auth gates (10 endpoints)
    - Enum completeness checks (5 enums)
    - Service helper tests (status transitions, stats)

~60 tests covering the full Career Action Planner pipeline.
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_career_action_plan_model_creation(db_session):
    """Test CareerActionPlan model can be created."""
    from app.core.security import hash_password
    from app.models.career_action_planner import CareerActionPlan
    from app.models.career_dna import CareerDNA
    from app.models.user import User

    user = User(
        email="plan@planner.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Plan User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    plan = CareerActionPlan(
        career_dna_id=career_dna.id,
        user_id=user.id,
        title="Skill Development Sprint — 4-Week",
        objective="Master cloud architecture fundamentals",
        plan_type="skill_development",
        status="draft",
        priority_score=72.5,
        confidence=0.68,
    )
    db_session.add(plan)
    await db_session.flush()

    assert plan.id is not None
    assert plan.title == "Skill Development Sprint — 4-Week"
    assert plan.plan_type == "skill_development"
    assert plan.status == "draft"
    assert plan.confidence == 0.68
    assert "AI-powered" in plan.data_source
    assert "AI-generated" in plan.disclaimer


@pytest.mark.asyncio
async def test_plan_milestone_model_creation(db_session):
    """Test PlanMilestone model can be created."""
    from app.core.security import hash_password
    from app.models.career_action_planner import CareerActionPlan, PlanMilestone
    from app.models.career_dna import CareerDNA
    from app.models.user import User

    user = User(
        email="milestone@planner.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Milestone User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    plan = CareerActionPlan(
        career_dna_id=career_dna.id,
        user_id=user.id,
        title="Test Plan",
        objective="Test objective",
        plan_type="skill_development",
        status="draft",
        priority_score=50.0,
        confidence=0.5,
    )
    db_session.add(plan)
    await db_session.flush()

    milestone = PlanMilestone(
        plan_id=plan.id,
        title="Complete AWS Solutions Architect course",
        description="Finish all modules and labs",
        category="certification",
        target_date=date.today() + timedelta(weeks=2),
        status="not_started",
        effort_hours=20,
        priority=1,
        evidence_required="Certificate of completion",
    )
    db_session.add(milestone)
    await db_session.flush()

    assert milestone.id is not None
    assert milestone.title == "Complete AWS Solutions Architect course"
    assert milestone.category == "certification"
    assert milestone.effort_hours == 20
    assert milestone.priority == 1


@pytest.mark.asyncio
async def test_milestone_progress_model_creation(db_session):
    """Test MilestoneProgress model can be created."""
    from datetime import datetime, timezone

    from app.core.security import hash_password
    from app.models.career_action_planner import (
        CareerActionPlan,
        MilestoneProgress,
        PlanMilestone,
    )
    from app.models.career_dna import CareerDNA
    from app.models.user import User

    user = User(
        email="progress@planner.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Progress User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    plan = CareerActionPlan(
        career_dna_id=career_dna.id,
        user_id=user.id,
        title="Progress Plan",
        objective="Test",
        plan_type="skill_development",
        status="active",
        priority_score=60.0,
        confidence=0.55,
    )
    db_session.add(plan)
    await db_session.flush()

    milestone = PlanMilestone(
        plan_id=plan.id,
        title="Learn Docker",
        category="learning",
        status="in_progress",
        effort_hours=10,
        priority=2,
    )
    db_session.add(milestone)
    await db_session.flush()

    progress = MilestoneProgress(
        milestone_id=milestone.id,
        progress_percent=45.0,
        notes="Completed Docker basics module",
        evidence_url="https://example.com/cert",
        logged_at=datetime.now(tz=timezone.utc),  # noqa: UP017
    )
    db_session.add(progress)
    await db_session.flush()

    assert progress.id is not None
    assert progress.progress_percent == 45.0
    assert progress.notes == "Completed Docker basics module"


@pytest.mark.asyncio
async def test_plan_recommendation_model_creation(db_session):
    """Test PlanRecommendation model can be created."""
    from app.core.security import hash_password
    from app.models.career_action_planner import CareerActionPlan, PlanRecommendation
    from app.models.career_dna import CareerDNA
    from app.models.user import User

    user = User(
        email="rec@planner.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Rec User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    plan = CareerActionPlan(
        career_dna_id=career_dna.id,
        user_id=user.id,
        title="Rec Plan",
        objective="Test",
        plan_type="role_transition",
        status="active",
        priority_score=70.0,
        confidence=0.6,
    )
    db_session.add(plan)
    await db_session.flush()

    rec = PlanRecommendation(
        plan_id=plan.id,
        source_engine="threat_radar",
        recommendation_type="skill_acquisition",
        title="Learn Kubernetes",
        rationale="K8s adoption growing 40% YoY in your industry",
        urgency="high",
        impact_score=85.0,
    )
    db_session.add(rec)
    await db_session.flush()

    assert rec.id is not None
    assert rec.source_engine == "threat_radar"
    assert rec.urgency == "high"
    assert rec.impact_score == 85.0


@pytest.mark.asyncio
async def test_planner_preference_model_creation(db_session):
    """Test CareerActionPlannerPreference model can be created."""
    from app.core.security import hash_password
    from app.models.career_action_planner import CareerActionPlannerPreference
    from app.models.career_dna import CareerDNA
    from app.models.user import User

    user = User(
        email="planner_pref@planner.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = CareerActionPlannerPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
        preferred_sprint_length_weeks=6,
        max_milestones_per_plan=7,
        notification_frequency="weekly",
        auto_generate_recommendations=True,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.preferred_sprint_length_weeks == 6
    assert pref.max_milestones_per_plan == 7
    assert pref.auto_generate_recommendations is True


# ── Static Helper Tests ────────────────────────────────────────


def test_clamp_confidence_caps_at_085():
    """Even perfect confidence cannot exceed 0.85."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_confidence(1.0) <= 0.85


def test_clamp_confidence_zero_input():
    """Zero input returns 0.0."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_confidence(0.0) == 0.0


def test_clamp_confidence_negative_input():
    """Negative input is clamped to 0.0."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_confidence(-0.5) == 0.0


def test_clamp_confidence_non_numeric():
    """Non-numeric input returns 0.0."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_confidence("invalid") == 0.0  # type: ignore[arg-type]


def test_clamp_impact_score_range():
    """Impact score clamped to [0, 100]."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_impact_score(150.0) == 100.0
    assert CareerActionPlannerAnalyzer.clamp_impact_score(-10.0) == 0.0
    assert CareerActionPlannerAnalyzer.clamp_impact_score(75.5) == 75.5


def test_clamp_impact_score_non_numeric():
    """Non-numeric impact score returns 0.0."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    assert CareerActionPlannerAnalyzer.clamp_impact_score("high") == 0.0  # type: ignore[arg-type]


def test_build_priority_context_with_data():
    """Context builder formats Career DNA fields correctly."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    context = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role="Backend Engineer",
        primary_industry="FinTech",
        seniority_level="senior",
        location="Amsterdam",
        skills=["Python", "FastAPI", "PostgreSQL"],
    )
    assert context["primary_role"] == "Backend Engineer"
    assert context["primary_industry"] == "FinTech"
    assert "Python" in context["skills"]
    assert context["seniority_level"] == "senior"


def test_build_priority_context_empty_data():
    """Context builder handles None/empty gracefully."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    context = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role=None,
        primary_industry=None,
        seniority_level=None,
        location=None,
        skills=[],
    )
    assert context["primary_role"] == "Not specified"
    assert context["skills"] == "No skills listed"


def test_validate_milestone_timeline_within_range():
    """Target date within sprint range is kept."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    target = date.today() + timedelta(weeks=2)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=target, sprint_weeks=4,
    )
    assert result == target


def test_validate_milestone_timeline_past_date():
    """Past target date is shifted to next week."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    past = date.today() - timedelta(days=10)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=past, sprint_weeks=4,
    )
    assert result is not None
    assert result >= date.today()


def test_validate_milestone_timeline_far_future():
    """Far future date is clamped to sprint end."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    future = date.today() + timedelta(weeks=52)
    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=future, sprint_weeks=4,
    )
    assert result is not None
    max_date = date.today() + timedelta(weeks=6)
    assert result <= max_date


def test_validate_milestone_timeline_none():
    """None target date returns None."""
    from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer

    result = CareerActionPlannerAnalyzer.validate_milestone_timeline(
        target_date=None, sprint_weeks=4,
    )
    assert result is None


# ── Clamping Validator Tests ───────────────────────────────────


def test_clamp_priorities_caps_confidence():
    """Priority confidence above 0.85 is clamped."""
    from app.ai.career_action_planner_analyzer import _clamp_priorities

    data = {
        "confidence": 0.95,
        "priorities": [],
        "overall_assessment": "Test assessment",
    }
    _clamp_priorities(data)
    assert data["confidence"] <= 0.85


def test_clamp_priorities_validates_urgency():
    """Invalid urgency defaults to medium."""
    from app.ai.career_action_planner_analyzer import _clamp_priorities

    data = {
        "confidence": 0.5,
        "priorities": [
            {
                "title": "Test",
                "description": "Test",
                "urgency": "super_critical",
                "impact_score": 50.0,
                "category": "learning",
                "rationale": "Test",
            },
        ],
    }
    _clamp_priorities(data)
    assert data["priorities"][0]["urgency"] == "medium"


def test_clamp_priorities_caps_impact_score():
    """Impact score above 100 is clamped."""
    from app.ai.career_action_planner_analyzer import _clamp_priorities

    data = {
        "confidence": 0.5,
        "priorities": [
            {
                "title": "Test",
                "description": "Test",
                "urgency": "high",
                "impact_score": 150.0,
                "category": "learning",
                "rationale": "Test",
            },
        ],
    }
    _clamp_priorities(data)
    assert data["priorities"][0]["impact_score"] <= 100.0


def test_clamp_priorities_validates_category():
    """Invalid category defaults to learning."""
    from app.ai.career_action_planner_analyzer import _clamp_priorities

    data = {
        "confidence": 0.5,
        "priorities": [
            {
                "title": "Test",
                "description": "Test",
                "urgency": "high",
                "impact_score": 50.0,
                "category": "unknown_category",
                "rationale": "Test",
            },
        ],
    }
    _clamp_priorities(data)
    assert data["priorities"][0]["category"] == "learning"


def test_clamp_priorities_max_5():
    """Priorities list is capped at 5 items."""
    from app.ai.career_action_planner_analyzer import _clamp_priorities

    data = {
        "confidence": 0.5,
        "priorities": [
            {
                "title": f"Priority {i}",
                "description": "Test",
                "urgency": "medium",
                "impact_score": 50.0,
                "category": "learning",
                "rationale": "Test",
            }
            for i in range(10)
        ],
    }
    _clamp_priorities(data)
    assert len(data["priorities"]) == 5


def test_clamp_milestones_caps_effort():
    """Effort hours clamped to 1-120 range."""
    from app.ai.career_action_planner_analyzer import _clamp_milestones

    data = {
        "confidence": 0.5,
        "milestones": [
            {
                "title": "Test",
                "description": "Test",
                "category": "learning",
                "effort_hours": 200,
                "priority": 1,
                "evidence_required": "Cert",
            },
        ],
    }
    _clamp_milestones(data, max_milestones=5)
    assert data["milestones"][0]["effort_hours"] == 120


def test_clamp_milestones_caps_priority():
    """Priority clamped to 1-10 range."""
    from app.ai.career_action_planner_analyzer import _clamp_milestones

    data = {
        "confidence": 0.5,
        "milestones": [
            {
                "title": "Test",
                "description": "Test",
                "category": "learning",
                "effort_hours": 8,
                "priority": 15,
                "evidence_required": "Cert",
            },
        ],
    }
    _clamp_milestones(data, max_milestones=5)
    assert data["milestones"][0]["priority"] == 10


def test_clamp_milestones_validates_category():
    """Invalid milestone category defaults to learning."""
    from app.ai.career_action_planner_analyzer import _clamp_milestones

    data = {
        "confidence": 0.5,
        "milestones": [
            {
                "title": "Test",
                "category": "unknown",
                "effort_hours": 8,
                "priority": 1,
            },
        ],
    }
    _clamp_milestones(data, max_milestones=5)
    assert data["milestones"][0]["category"] == "learning"


def test_clamp_progress_evaluation_validates_health():
    """Invalid plan health defaults to at_risk."""
    from app.ai.career_action_planner_analyzer import _clamp_progress_evaluation

    data = {
        "confidence": 0.5,
        "plan_health": "super_good",
        "overall_progress_percent": 50.0,
    }
    _clamp_progress_evaluation(data)
    assert data["plan_health"] == "at_risk"


def test_clamp_progress_evaluation_caps_progress():
    """Progress percent capped at 100."""
    from app.ai.career_action_planner_analyzer import _clamp_progress_evaluation

    data = {
        "confidence": 0.5,
        "plan_health": "on_track",
        "overall_progress_percent": 150.0,
    }
    _clamp_progress_evaluation(data)
    assert data["overall_progress_percent"] <= 100.0


def test_clamp_progress_evaluation_valid_health():
    """Valid plan health values are preserved."""
    from app.ai.career_action_planner_analyzer import _clamp_progress_evaluation

    for health_val in ("on_track", "at_risk", "behind", "ahead"):
        data = {
            "confidence": 0.5,
            "plan_health": health_val,
            "overall_progress_percent": 50.0,
        }
        _clamp_progress_evaluation(data)
        assert data["plan_health"] == health_val


def test_clamp_recommendations_validates_engine():
    """Invalid source engine defaults to predictive_career."""
    from app.ai.career_action_planner_analyzer import _clamp_recommendations

    data = {
        "confidence": 0.5,
        "recommendations": [
            {
                "source_engine": "invalid_engine",
                "title": "Test",
                "urgency": "high",
                "impact_score": 50.0,
                "rationale": "Test",
                "recommendation_type": "general",
            },
        ],
    }
    _clamp_recommendations(data)
    assert data["recommendations"][0]["source_engine"] == "predictive_career"


def test_clamp_recommendations_valid_engines():
    """Valid source engines are preserved."""
    from app.ai.career_action_planner_analyzer import _clamp_recommendations

    valid_engines = [
        "threat_radar", "skill_decay", "salary_intelligence",
        "transition_pathways", "career_simulation", "hidden_job_market",
    ]
    for engine in valid_engines:
        data = {
            "confidence": 0.5,
            "recommendations": [
                {
                    "source_engine": engine,
                    "title": "Test",
                    "urgency": "medium",
                    "impact_score": 50.0,
                    "rationale": "Test",
                    "recommendation_type": "general",
                },
            ],
        }
        _clamp_recommendations(data)
        assert data["recommendations"][0]["source_engine"] == engine


def test_clamp_recommendations_max_5():
    """Recommendations list is capped at 5."""
    from app.ai.career_action_planner_analyzer import _clamp_recommendations

    data = {
        "confidence": 0.5,
        "recommendations": [
            {
                "source_engine": "threat_radar",
                "title": f"Rec {i}",
                "urgency": "medium",
                "impact_score": 50.0,
                "rationale": "Test",
                "recommendation_type": "general",
            }
            for i in range(10)
        ],
    }
    _clamp_recommendations(data)
    assert len(data["recommendations"]) == 5


# ── Schema Validation Tests ────────────────────────────────────


def test_generate_plan_request_valid():
    """GeneratePlanRequest validates correctly."""
    from app.schemas.career_action_planner import GeneratePlanRequest

    request = GeneratePlanRequest(
        plan_type="skill_development",
        focus_area="Cloud architecture",
        target_timeline_weeks=4,
    )
    assert request.plan_type == "skill_development"
    assert request.target_timeline_weeks == 4


def test_generate_plan_request_defaults():
    """GeneratePlanRequest has sensible defaults."""
    from app.schemas.career_action_planner import GeneratePlanRequest

    request = GeneratePlanRequest(plan_type="role_transition")
    assert request.target_timeline_weeks == 4
    assert request.focus_area is None


def test_generate_plan_request_rejects_empty_type():
    """GeneratePlanRequest rejects empty plan type."""
    from pydantic import ValidationError

    from app.schemas.career_action_planner import GeneratePlanRequest

    with pytest.raises(ValidationError):
        GeneratePlanRequest(plan_type="")


def test_generate_plan_request_rejects_long_timeline():
    """GeneratePlanRequest rejects timeline > 12 weeks."""
    from pydantic import ValidationError

    from app.schemas.career_action_planner import GeneratePlanRequest

    with pytest.raises(ValidationError):
        GeneratePlanRequest(
            plan_type="skill_development",
            target_timeline_weeks=52,
        )


def test_update_plan_status_request_valid():
    """UpdatePlanStatusRequest validates correctly."""
    from app.schemas.career_action_planner import UpdatePlanStatusRequest

    request = UpdatePlanStatusRequest(status="active")
    assert request.status == "active"


def test_update_milestone_request_partial():
    """UpdateMilestoneRequest handles partial updates."""
    from app.schemas.career_action_planner import UpdateMilestoneRequest

    request = UpdateMilestoneRequest(
        status="in_progress",
        effort_hours=16,
    )
    assert request.status == "in_progress"
    assert request.effort_hours == 16
    assert request.target_date is None
    assert request.priority is None


def test_log_progress_request_valid():
    """LogProgressRequest validates correctly."""
    from app.schemas.career_action_planner import LogProgressRequest

    request = LogProgressRequest(
        progress_percent=75.0,
        notes="Completed 3 of 4 modules",
        evidence_url="https://example.com/cert",
    )
    assert request.progress_percent == 75.0


def test_log_progress_request_rejects_over_100():
    """LogProgressRequest rejects progress > 100."""
    from pydantic import ValidationError

    from app.schemas.career_action_planner import LogProgressRequest

    with pytest.raises(ValidationError):
        LogProgressRequest(progress_percent=150.0)


def test_preference_update_partial():
    """CareerActionPlannerPreferenceUpdate handles partial updates."""
    from app.schemas.career_action_planner import CareerActionPlannerPreferenceUpdate

    request = CareerActionPlannerPreferenceUpdate(
        preferred_sprint_length_weeks=6,
        auto_generate_recommendations=False,
    )
    assert request.preferred_sprint_length_weeks == 6
    assert request.auto_generate_recommendations is False
    assert request.max_milestones_per_plan is None
    assert request.notification_frequency is None


def test_plan_action_response_confidence_bound():
    """CareerActionPlanResponse enforces confidence <= 0.85."""
    from pydantic import ValidationError

    from app.schemas.career_action_planner import CareerActionPlanResponse

    with pytest.raises(ValidationError):
        CareerActionPlanResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            title="Test",
            objective="Test",
            plan_type="skill_development",
            status="draft",
            priority_score=50.0,
            confidence=0.95,
            data_source="AI",
            disclaimer="Test",
            created_at="2026-01-01T00:00:00",
        )


def test_dashboard_response_defaults():
    """PlanDashboardResponse has correct defaults."""
    from app.schemas.career_action_planner import PlanDashboardResponse, PlanStatsResponse

    response = PlanDashboardResponse(stats=PlanStatsResponse())
    assert response.active_plans == []
    assert response.recent_recommendations == []
    assert "85%" in response.disclaimer


def test_plan_stats_response_defaults():
    """PlanStatsResponse has zero defaults."""
    from app.schemas.career_action_planner import PlanStatsResponse

    stats = PlanStatsResponse()
    assert stats.total_plans == 0
    assert stats.active_plans == 0
    assert stats.overall_progress_percent == 0.0


def test_plan_comparison_response_defaults():
    """PlanComparisonResponse has correct defaults."""
    from app.schemas.career_action_planner import PlanComparisonResponse

    response = PlanComparisonResponse()
    assert response.plans == []
    assert response.recommended_plan_id is None
    assert "85%" in response.disclaimer


# ── API Auth Gate Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_planner_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-action-planner/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_scan_requires_auth(client: AsyncClient):
    """Plan generation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-action-planner/scan",
        json={"plan_type": "skill_development"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_get_plan_requires_auth(client: AsyncClient):
    """Get plan endpoint returns 401 without auth."""
    plan_id = uuid.uuid4()
    response = await client.get(f"/api/v1/career-action-planner/{plan_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_update_plan_status_requires_auth(client: AsyncClient):
    """Update plan status returns 401 without auth."""
    plan_id = uuid.uuid4()
    response = await client.put(
        f"/api/v1/career-action-planner/{plan_id}/status",
        json={"status": "active"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_list_milestones_requires_auth(client: AsyncClient):
    """List milestones endpoint returns 401 without auth."""
    plan_id = uuid.uuid4()
    response = await client.get(f"/api/v1/career-action-planner/{plan_id}/milestones")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_update_milestone_requires_auth(client: AsyncClient):
    """Update milestone endpoint returns 401 without auth."""
    plan_id = uuid.uuid4()
    milestone_id = uuid.uuid4()
    response = await client.put(
        f"/api/v1/career-action-planner/{plan_id}/milestones/{milestone_id}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_log_progress_requires_auth(client: AsyncClient):
    """Log progress endpoint returns 401 without auth."""
    plan_id = uuid.uuid4()
    milestone_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/career-action-planner/{plan_id}/milestones/{milestone_id}/progress",
        json={"progress_percent": 50.0},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_compare_plans_requires_auth(client: AsyncClient):
    """Compare plans endpoint returns 401 without auth."""
    response = await client.post("/api/v1/career-action-planner/compare")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_get_preferences_requires_auth(client: AsyncClient):
    """Get preferences endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-action-planner/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_planner_update_preferences_requires_auth(client: AsyncClient):
    """Update preferences endpoint returns 401 without auth."""
    response = await client.put(
        "/api/v1/career-action-planner/preferences",
        json={"preferred_sprint_length_weeks": 6},
    )
    assert response.status_code == 401


# ── Enum Completeness Tests ────────────────────────────────────


def test_plan_type_enum_completeness():
    """PlanType enum has all 5 types."""
    from app.models.career_action_planner import PlanType

    types = list(PlanType)
    assert len(types) == 5
    assert PlanType.SKILL_DEVELOPMENT in types
    assert PlanType.ROLE_TRANSITION in types
    assert PlanType.SALARY_GROWTH in types
    assert PlanType.THREAT_MITIGATION in types
    assert PlanType.OPPORTUNITY_CAPTURE in types


def test_plan_status_enum_completeness():
    """PlanStatus enum has 5 statuses."""
    from app.models.career_action_planner import PlanStatus

    statuses = list(PlanStatus)
    assert len(statuses) == 5
    assert PlanStatus.DRAFT in statuses
    assert PlanStatus.ACTIVE in statuses
    assert PlanStatus.PAUSED in statuses
    assert PlanStatus.COMPLETED in statuses
    assert PlanStatus.ARCHIVED in statuses


def test_milestone_category_enum_completeness():
    """MilestoneCategory enum has 6 categories."""
    from app.models.career_action_planner import MilestoneCategory

    categories = list(MilestoneCategory)
    assert len(categories) == 6
    assert MilestoneCategory.LEARNING in categories
    assert MilestoneCategory.CERTIFICATION in categories
    assert MilestoneCategory.NETWORKING in categories
    assert MilestoneCategory.PROJECT in categories
    assert MilestoneCategory.APPLICATION in categories
    assert MilestoneCategory.INTERVIEW_PREP in categories


def test_milestone_status_enum_completeness():
    """MilestoneStatus enum has 5 statuses."""
    from app.models.career_action_planner import MilestoneStatus

    statuses = list(MilestoneStatus)
    assert len(statuses) == 5
    assert MilestoneStatus.NOT_STARTED in statuses
    assert MilestoneStatus.IN_PROGRESS in statuses
    assert MilestoneStatus.COMPLETED in statuses
    assert MilestoneStatus.SKIPPED in statuses
    assert MilestoneStatus.BLOCKED in statuses


def test_source_engine_enum_completeness():
    """SourceEngine enum has 8 engines."""
    from app.models.career_action_planner import SourceEngine

    engines = list(SourceEngine)
    assert len(engines) == 8
    assert SourceEngine.THREAT_RADAR in engines
    assert SourceEngine.SKILL_DECAY in engines
    assert SourceEngine.SALARY_INTELLIGENCE in engines
    assert SourceEngine.TRANSITION_PATHWAYS in engines
    assert SourceEngine.CAREER_SIMULATION in engines
    assert SourceEngine.HIDDEN_JOB_MARKET in engines
    assert SourceEngine.PREDICTIVE_CAREER in engines
    assert SourceEngine.COLLECTIVE_INTELLIGENCE in engines


# ── Service Status Transition Tests ────────────────────────────


def test_valid_status_transitions():
    """Valid status transitions are defined correctly."""
    from app.services.career_action_planner_service import VALID_STATUS_TRANSITIONS

    # Draft can go to active or archived
    assert "active" in VALID_STATUS_TRANSITIONS["draft"]
    assert "archived" in VALID_STATUS_TRANSITIONS["draft"]

    # Active can go to paused, completed, archived
    assert "paused" in VALID_STATUS_TRANSITIONS["active"]
    assert "completed" in VALID_STATUS_TRANSITIONS["active"]
    assert "archived" in VALID_STATUS_TRANSITIONS["active"]

    # Paused can go to active or archived
    assert "active" in VALID_STATUS_TRANSITIONS["paused"]
    assert "archived" in VALID_STATUS_TRANSITIONS["paused"]

    # Completed can only go to archived
    assert "archived" in VALID_STATUS_TRANSITIONS["completed"]
    assert len(VALID_STATUS_TRANSITIONS["completed"]) == 1

    # Archived is terminal
    assert len(VALID_STATUS_TRANSITIONS["archived"]) == 0


def test_plan_type_labels():
    """Plan type labels are human-readable."""
    from app.services.career_action_planner_service import PLAN_TYPE_LABELS

    assert "Skill Development" in PLAN_TYPE_LABELS["skill_development"]
    assert "Role Transition" in PLAN_TYPE_LABELS["role_transition"]
    assert "Salary Growth" in PLAN_TYPE_LABELS["salary_growth"]
    assert "Threat Mitigation" in PLAN_TYPE_LABELS["threat_mitigation"]
    assert "Opportunity Capture" in PLAN_TYPE_LABELS["opportunity_capture"]
