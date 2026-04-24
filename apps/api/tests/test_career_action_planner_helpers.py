"""
PathForge — Career Action Planner Helpers Unit Tests
=====================================================
Comprehensive coverage for pure helper functions in
app.services._career_action_planner_helpers.

Covers:
    aggregate_intelligence  — intelligence summary assembly
    compute_stats            — aggregate statistics computation
    compute_priority_score   — priority score aggregation
    compare_plans            — plan comparison pipeline
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_action_planner import (
    CareerActionPlan,
    MilestoneStatus,
    PlanMilestone,
    PlanStatus,
    PlanType,
)
from app.models.career_dna import CareerDNA
from app.models.user import User
from app.services._career_action_planner_helpers import (
    ComparePlansResult,
    DashboardResult,
    GeneratePlanResult,
    aggregate_intelligence,
    compare_plans,
    compute_priority_score,
    compute_stats,
)

# ── Helpers for DB-backed tests ─────────────────────────────────


async def _make_user_and_dna(
    db: AsyncSession, *, email: str = "helpers@pathforge.eu",
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Helper Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="mid",
        location="Utrecht",
    )
    db.add(dna)
    await db.flush()
    return user, dna


async def _make_plan(
    db: AsyncSession,
    *,
    user: User,
    dna: CareerDNA,
    title: str = "Plan",
    priority_score: float = 50.0,
    status: str = PlanStatus.ACTIVE.value,
) -> CareerActionPlan:
    plan = CareerActionPlan(
        career_dna_id=str(dna.id),
        user_id=str(user.id),
        title=title,
        objective="Objective text",
        plan_type=PlanType.SKILL_DEVELOPMENT.value,
        status=status,
        priority_score=priority_score,
        confidence=0.8,
    )
    db.add(plan)
    await db.flush()
    return plan


async def _make_milestone(
    db: AsyncSession,
    *,
    plan: CareerActionPlan,
    title: str = "Milestone",
    status: str = MilestoneStatus.NOT_STARTED.value,
) -> PlanMilestone:
    milestone = PlanMilestone(
        plan_id=str(plan.id),
        title=title,
        description="Milestone description",
        category="learning",
        target_date=date.today() + timedelta(weeks=1),
        status=status,
        effort_hours=4,
        priority=5,
    )
    db.add(milestone)
    await db.flush()
    return milestone


# ── DTO Construction Tests ──────────────────────────────────────


def test_dashboard_result_is_frozen() -> None:
    result = DashboardResult(
        active_plans=[],
        recent_recommendations=[],
        stats={"total_plans": 0},
        preferences=None,
    )
    assert result.active_plans == []
    assert result.stats == {"total_plans": 0}
    assert result.preferences is None
    with pytest.raises((AttributeError, Exception)):
        result.active_plans = [{"x": 1}]  # type: ignore[misc]


def test_generate_plan_result_structure() -> None:
    plan = MagicMock(spec=CareerActionPlan)
    result = GeneratePlanResult(plan=plan, recommendations=[])
    assert result.plan is plan
    assert result.recommendations == []


def test_compare_plans_result_structure() -> None:
    pid = uuid.uuid4()
    result = ComparePlansResult(
        plans=[],
        recommended_plan_id=pid,
        recommendation_reasoning="Reason",
    )
    assert result.recommended_plan_id == pid
    assert result.recommendation_reasoning == "Reason"
    assert result.plans == []


# ── aggregate_intelligence Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_aggregate_intelligence_empty_returns_default() -> None:
    dna = SimpleNamespace()
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert result == "No recent intelligence data available."


@pytest.mark.asyncio
async def test_aggregate_intelligence_all_none_returns_default() -> None:
    dna = SimpleNamespace(
        automation_risk=None,
        threat_alerts=[],
        skill_freshness=[],
        growth_vector=None,
        market_position=None,
    )
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert result == "No recent intelligence data available."


@pytest.mark.asyncio
async def test_aggregate_intelligence_with_automation_risk() -> None:
    risk = SimpleNamespace(risk_score=75.4, risk_level="high")
    dna = SimpleNamespace(automation_risk=risk)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Automation Risk: 75% (high level)" in result
    assert result.startswith("- ")


@pytest.mark.asyncio
async def test_aggregate_intelligence_risk_score_none_skipped() -> None:
    risk = SimpleNamespace(risk_score=None, risk_level="unknown")
    dna = SimpleNamespace(automation_risk=risk)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert result == "No recent intelligence data available."


@pytest.mark.asyncio
async def test_aggregate_intelligence_risk_missing_level() -> None:
    # risk_score present but risk_level missing → "unknown"
    risk = SimpleNamespace(risk_score=42.0)
    dna = SimpleNamespace(automation_risk=risk)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Automation Risk: 42% (unknown level)" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_with_threat_alerts() -> None:
    alerts = [
        SimpleNamespace(title="Alert A"),
        SimpleNamespace(title="Alert B"),
        SimpleNamespace(title="Alert C"),
        SimpleNamespace(title="Alert D"),  # beyond [:3]
    ]
    dna = SimpleNamespace(threat_alerts=alerts)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Recent Threat Alerts: Alert A, Alert B, Alert C" in result
    assert "Alert D" not in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_threat_alerts_missing_title() -> None:
    alerts = [SimpleNamespace()]  # no title attribute → "Unknown"
    dna = SimpleNamespace(threat_alerts=alerts)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Recent Threat Alerts: Unknown" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_decaying_skills() -> None:
    freshness = [
        SimpleNamespace(skill_name="Perl", freshness_score=0.2),
        SimpleNamespace(skill_name="COBOL", freshness_score=0.1),
        SimpleNamespace(skill_name="Python", freshness_score=0.9),  # not decaying
    ]
    dna = SimpleNamespace(skill_freshness=freshness)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Decaying Skills: Perl, COBOL" in result
    assert "Python" not in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_decaying_skills_truncated_to_five() -> None:
    freshness = [
        SimpleNamespace(skill_name=f"Skill{i}", freshness_score=0.1)
        for i in range(8)
    ]
    dna = SimpleNamespace(skill_freshness=freshness)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Skill0, Skill1, Skill2, Skill3, Skill4" in result
    assert "Skill5" not in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_no_decaying_skills() -> None:
    freshness = [
        SimpleNamespace(skill_name="Python", freshness_score=0.8),
        SimpleNamespace(skill_name="TypeScript", freshness_score=0.95),
    ]
    dna = SimpleNamespace(skill_freshness=freshness)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert result == "No recent intelligence data available."


@pytest.mark.asyncio
async def test_aggregate_intelligence_skill_freshness_missing_name() -> None:
    freshness = [SimpleNamespace(freshness_score=0.3)]
    dna = SimpleNamespace(skill_freshness=freshness)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Unknown" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_growth_vector() -> None:
    vector = SimpleNamespace(
        current_trajectory="accelerating",
        growth_score=82.5,
    )
    dna = SimpleNamespace(growth_vector=vector)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Growth Trajectory: accelerating (score: 82.5)" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_growth_vector_defaults() -> None:
    vector = SimpleNamespace()
    dna = SimpleNamespace(growth_vector=vector)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Growth Trajectory: steady (score: 50.0)" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_market_position() -> None:
    position = SimpleNamespace(
        percentile_overall=87.0,
        market_trend="rising",
    )
    dna = SimpleNamespace(market_position=position)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Market Position: 87th percentile (rising)" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_market_position_defaults() -> None:
    position = SimpleNamespace()
    dna = SimpleNamespace(market_position=position)
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert "Market Position: 50th percentile (stable)" in result


@pytest.mark.asyncio
async def test_aggregate_intelligence_all_sections_joined() -> None:
    dna = SimpleNamespace(
        automation_risk=SimpleNamespace(risk_score=30.0, risk_level="low"),
        threat_alerts=[SimpleNamespace(title="AI")],
        skill_freshness=[SimpleNamespace(skill_name="jQuery", freshness_score=0.1)],
        growth_vector=SimpleNamespace(
            current_trajectory="steady", growth_score=60.0,
        ),
        market_position=SimpleNamespace(
            percentile_overall=70.0, market_trend="stable",
        ),
    )
    result = await aggregate_intelligence(MagicMock(), dna)  # type: ignore[arg-type]
    assert result.count("\n") == 4  # 5 parts → 4 newlines
    assert "Automation Risk" in result
    assert "Recent Threat Alerts" in result
    assert "Decaying Skills" in result
    assert "Growth Trajectory" in result
    assert "Market Position" in result


# ── compute_stats Tests ─────────────────────────────────────────


def test_compute_stats_empty_list() -> None:
    stats = compute_stats([])
    assert stats["total_plans"] == 0
    assert stats["active_plans"] == 0
    assert stats["completed_plans"] == 0
    assert stats["total_milestones"] == 0
    assert stats["completed_milestones"] == 0
    assert stats["overall_progress_percent"] == 0.0


def test_compute_stats_counts_active_and_completed() -> None:
    plans = [
        SimpleNamespace(status=PlanStatus.ACTIVE.value, milestones=[]),
        SimpleNamespace(status=PlanStatus.ACTIVE.value, milestones=[]),
        SimpleNamespace(status=PlanStatus.COMPLETED.value, milestones=[]),
        SimpleNamespace(status=PlanStatus.DRAFT.value, milestones=[]),
    ]
    stats = compute_stats(plans)  # type: ignore[arg-type]
    assert stats["total_plans"] == 4
    assert stats["active_plans"] == 2
    assert stats["completed_plans"] == 1


def test_compute_stats_milestone_progress() -> None:
    milestones = [
        SimpleNamespace(status=MilestoneStatus.COMPLETED.value),
        SimpleNamespace(status=MilestoneStatus.COMPLETED.value),
        SimpleNamespace(status=MilestoneStatus.NOT_STARTED.value),
        SimpleNamespace(status=MilestoneStatus.IN_PROGRESS.value),
    ]
    plans = [
        SimpleNamespace(
            status=PlanStatus.ACTIVE.value, milestones=milestones,
        ),
    ]
    stats = compute_stats(plans)  # type: ignore[arg-type]
    assert stats["total_milestones"] == 4
    assert stats["completed_milestones"] == 2
    assert stats["overall_progress_percent"] == 50.0


def test_compute_stats_no_milestones_on_plan() -> None:
    plans = [
        SimpleNamespace(status=PlanStatus.ACTIVE.value, milestones=None),
        SimpleNamespace(status=PlanStatus.ACTIVE.value, milestones=[]),
    ]
    stats = compute_stats(plans)  # type: ignore[arg-type]
    assert stats["total_milestones"] == 0
    assert stats["overall_progress_percent"] == 0.0


def test_compute_stats_progress_rounded() -> None:
    milestones = [
        SimpleNamespace(status=MilestoneStatus.COMPLETED.value),
        SimpleNamespace(status=MilestoneStatus.NOT_STARTED.value),
        SimpleNamespace(status=MilestoneStatus.NOT_STARTED.value),
    ]
    plans = [
        SimpleNamespace(
            status=PlanStatus.ACTIVE.value, milestones=milestones,
        ),
    ]
    stats = compute_stats(plans)  # type: ignore[arg-type]
    # 1/3 * 100 = 33.333... rounded to 33.33
    assert stats["overall_progress_percent"] == 33.33


def test_compute_stats_fully_completed() -> None:
    milestones = [
        SimpleNamespace(status=MilestoneStatus.COMPLETED.value),
        SimpleNamespace(status=MilestoneStatus.COMPLETED.value),
    ]
    plans = [
        SimpleNamespace(
            status=PlanStatus.COMPLETED.value, milestones=milestones,
        ),
    ]
    stats = compute_stats(plans)  # type: ignore[arg-type]
    assert stats["overall_progress_percent"] == 100.0


# ── compute_priority_score Tests ────────────────────────────────


def test_compute_priority_score_empty_priorities() -> None:
    assert compute_priority_score({"priorities": []}) == 50.0


def test_compute_priority_score_missing_priorities_key() -> None:
    assert compute_priority_score({}) == 50.0


def test_compute_priority_score_simple_average() -> None:
    result = compute_priority_score({
        "priorities": [
            {"impact_score": 80.0},
            {"impact_score": 60.0},
        ],
    })
    assert result == 70.0


def test_compute_priority_score_default_impact() -> None:
    # Items without impact_score default to 50.0
    result = compute_priority_score({
        "priorities": [{"name": "x"}, {"name": "y"}],
    })
    assert result == 50.0


def test_compute_priority_score_clamped_upper() -> None:
    result = compute_priority_score({
        "priorities": [{"impact_score": 150.0}, {"impact_score": 200.0}],
    })
    assert result == 100.0


def test_compute_priority_score_clamped_lower() -> None:
    result = compute_priority_score({
        "priorities": [{"impact_score": -50.0}, {"impact_score": -100.0}],
    })
    assert result == 0.0


def test_compute_priority_score_filters_non_dict_entries() -> None:
    # Non-dict entries are filtered out
    result = compute_priority_score({
        "priorities": ["skip", None, {"impact_score": 90.0}],
    })
    assert result == 90.0


def test_compute_priority_score_all_non_dict_returns_default() -> None:
    result = compute_priority_score({
        "priorities": ["a", "b", 123],
    })
    assert result == 50.0


def test_compute_priority_score_returns_float_type() -> None:
    result = compute_priority_score({
        "priorities": [{"impact_score": 55.556}],
    })
    assert isinstance(result, float)
    assert result == 55.56  # rounded to 2 decimals


# ── compare_plans Tests (DB-backed) ──────────────────────────────


@pytest.mark.asyncio
async def test_compare_plans_no_plans(db_session: AsyncSession) -> None:
    user, _dna = await _make_user_and_dna(
        db_session, email="cmp-none@pathforge.eu",
    )
    result = await compare_plans(db_session, user_id=uuid.UUID(str(user.id)))
    assert result.plans == []
    assert result.recommended_plan_id is None
    assert result.recommendation_reasoning == "No plans found."


@pytest.mark.asyncio
async def test_compare_plans_single_plan(db_session: AsyncSession) -> None:
    user, dna = await _make_user_and_dna(
        db_session, email="cmp-one@pathforge.eu",
    )
    plan = await _make_plan(
        db_session, user=user, dna=dna, title="Solo", priority_score=42.0,
    )
    result = await compare_plans(db_session, user_id=uuid.UUID(str(user.id)))
    assert len(result.plans) == 1
    assert str(result.recommended_plan_id) == str(plan.id)
    assert "no comparison needed" in result.recommendation_reasoning.lower()


@pytest.mark.asyncio
async def test_compare_plans_picks_highest_priority(
    db_session: AsyncSession,
) -> None:
    user, dna = await _make_user_and_dna(
        db_session, email="cmp-multi@pathforge.eu",
    )
    await _make_plan(
        db_session, user=user, dna=dna, title="Low", priority_score=20.0,
    )
    winner = await _make_plan(
        db_session, user=user, dna=dna, title="High", priority_score=95.0,
    )
    await _make_plan(
        db_session, user=user, dna=dna, title="Mid", priority_score=50.0,
    )

    result = await compare_plans(db_session, user_id=uuid.UUID(str(user.id)))
    assert len(result.plans) == 3
    assert str(result.recommended_plan_id) == str(winner.id)
    assert "High" in result.recommendation_reasoning
    assert "95" in result.recommendation_reasoning


@pytest.mark.asyncio
async def test_compare_plans_with_specific_plan_ids(
    db_session: AsyncSession,
) -> None:
    user, dna = await _make_user_and_dna(
        db_session, email="cmp-ids@pathforge.eu",
    )
    p1 = await _make_plan(
        db_session, user=user, dna=dna, title="Alpha", priority_score=40.0,
    )
    p2 = await _make_plan(
        db_session, user=user, dna=dna, title="Beta", priority_score=80.0,
    )
    # Third plan is not in the filter
    await _make_plan(
        db_session, user=user, dna=dna, title="Gamma", priority_score=99.0,
    )

    result = await compare_plans(
        db_session,
        user_id=uuid.UUID(str(user.id)),
        plan_ids=[uuid.UUID(str(p1.id)), uuid.UUID(str(p2.id))],
    )
    assert len(result.plans) == 2
    # Gamma (99.0) is excluded, so Beta (80.0) wins
    assert str(result.recommended_plan_id) == str(p2.id)
    assert "Beta" in result.recommendation_reasoning


@pytest.mark.asyncio
async def test_compare_plans_specific_ids_single_result(
    db_session: AsyncSession,
) -> None:
    user, dna = await _make_user_and_dna(
        db_session, email="cmp-ids-one@pathforge.eu",
    )
    p1 = await _make_plan(
        db_session, user=user, dna=dna, title="OnlyOne", priority_score=10.0,
    )
    result = await compare_plans(
        db_session,
        user_id=uuid.UUID(str(user.id)),
        plan_ids=[uuid.UUID(str(p1.id))],
    )
    assert len(result.plans) == 1
    assert str(result.recommended_plan_id) == str(p1.id)
    assert "no comparison needed" in result.recommendation_reasoning.lower()


@pytest.mark.asyncio
async def test_compare_plans_specific_ids_none_match(
    db_session: AsyncSession,
) -> None:
    user, _dna = await _make_user_and_dna(
        db_session, email="cmp-ids-miss@pathforge.eu",
    )
    result = await compare_plans(
        db_session,
        user_id=uuid.UUID(str(user.id)),
        plan_ids=[uuid.uuid4(), uuid.uuid4()],
    )
    assert result.plans == []
    assert result.recommended_plan_id is None
    assert result.recommendation_reasoning == "No plans found."


@pytest.mark.asyncio
async def test_compare_plans_only_returns_users_plans(
    db_session: AsyncSession,
) -> None:
    user_a, dna_a = await _make_user_and_dna(
        db_session, email="cmp-owner-a@pathforge.eu",
    )
    user_b, dna_b = await _make_user_and_dna(
        db_session, email="cmp-owner-b@pathforge.eu",
    )
    await _make_plan(
        db_session, user=user_a, dna=dna_a, title="A-Plan", priority_score=70.0,
    )
    await _make_plan(
        db_session, user=user_b, dna=dna_b, title="B-Plan", priority_score=90.0,
    )
    # user_a only sees their one plan
    result = await compare_plans(
        db_session, user_id=uuid.UUID(str(user_a.id)),
    )
    assert len(result.plans) == 1
    assert result.plans[0].title == "A-Plan"


@pytest.mark.asyncio
async def test_compare_plans_uses_injected_session_mock() -> None:
    """Verify compare_plans uses the provided AsyncSession.execute."""
    session = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=exec_result)

    result = await compare_plans(
        session, user_id=uuid.uuid4(),
    )
    assert result.plans == []
    assert result.recommended_plan_id is None
    assert result.recommendation_reasoning == "No plans found."
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_compare_plans_reasoning_contains_score_formatted() -> None:
    """High-priority plan selection should format score with one decimal."""
    session = MagicMock()
    plan1 = MagicMock()
    plan1.id = uuid.uuid4()
    plan1.title = "Primary"
    plan1.priority_score = 88.75
    plan2 = MagicMock()
    plan2.id = uuid.uuid4()
    plan2.title = "Secondary"
    plan2.priority_score = 40.0

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [plan1, plan2]
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=exec_result)

    result = await compare_plans(session, user_id=uuid.uuid4())
    assert result.recommended_plan_id == plan1.id
    assert "Primary" in result.recommendation_reasoning
    assert "88.8" in result.recommendation_reasoning  # formatted .1f
    assert "/100" in result.recommendation_reasoning
