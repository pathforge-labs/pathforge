"""
PathForge — Career Action Planner Service Extended Unit Tests
===============================================================
Extended coverage targeting previously uncovered branches in
career_action_planner_service.py — milestone persistence, plan
retrieval, status transitions, milestone/progress updates, and
preferences CRUD.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_action_planner import (
    CareerActionPlan,
    CareerActionPlannerPreference,
    MilestoneStatus,
    PlanMilestone,
    PlanRecommendation,
    PlanStatus,
    PlanType,
)
from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.user import User
from app.schemas.career_action_planner import (
    CareerActionPlannerPreferenceUpdate,
    GeneratePlanRequest,
    LogProgressRequest,
    UpdateMilestoneRequest,
)
from app.services.career_action_planner_service import (
    generate_plan,
    get_dashboard,
    get_milestones,
    get_plan,
    get_preferences,
    log_progress,
    update_milestone,
    update_plan_status,
    update_preferences,
)

# ── Paths for patching ────────────────────────────────────────────

ANALYZER_PATH = (
    "app.services.career_action_planner_service.CareerActionPlannerAnalyzer"
)
AGGREGATE_PATH = (
    "app.services.career_action_planner_service.aggregate_intelligence"
)


# ── Helpers ───────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 3,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Planner Ext Tester",
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

    if with_skills:
        for i in range(skill_count):
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=f"Skill{i}",
                category="technical",
                proficiency_level="intermediate",
                confidence=0.75,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    return user, dna


async def _make_plan(
    db: AsyncSession,
    *,
    user: User,
    dna: CareerDNA,
    status: str = PlanStatus.DRAFT.value,
    plan_type: str = PlanType.SKILL_DEVELOPMENT.value,
    title: str = "Test Plan",
) -> CareerActionPlan:
    plan = CareerActionPlan(
        career_dna_id=str(dna.id),
        user_id=str(user.id),
        title=title,
        objective="Test objective",
        plan_type=plan_type,
        status=status,
        priority_score=50.0,
        confidence=0.7,
    )
    db.add(plan)
    await db.flush()
    return plan


async def _make_milestone(
    db: AsyncSession,
    *,
    plan: CareerActionPlan,
    title: str = "Test Milestone",
    status: str = MilestoneStatus.NOT_STARTED.value,
    priority: int = 5,
    category: str = "learning",
) -> PlanMilestone:
    milestone = PlanMilestone(
        plan_id=str(plan.id),
        title=title,
        description="Test description",
        category=category,
        target_date=date.today() + timedelta(weeks=2),
        status=status,
        effort_hours=8,
        priority=priority,
    )
    db.add(milestone)
    await db.flush()
    return milestone


def _analyzer_patches(
    *,
    priorities: dict | None = None,
    milestones: dict | None = None,
    recommendations: dict | None = None,
    confidence: float = 0.75,
    impact: float = 50.0,
) -> list:
    """Build a list of patch objects for generate_plan LLM mocks."""
    priorities_default = priorities or {
        "overall_assessment": "Default assessment",
        "priorities": [],
        "confidence": 0.8,
    }
    milestones_default = milestones or {"milestones": []}
    recs_default = recommendations or {"recommendations": []}

    context_mock = MagicMock(return_value={
        "primary_role": "Engineer",
        "primary_industry": "Tech",
        "seniority_level": "mid",
        "location": "Utrecht",
        "skills": ["Python"],
    })

    validated_date = date.today() + timedelta(weeks=1)

    return [
        patch(f"{ANALYZER_PATH}.build_priority_context", context_mock),
        patch(AGGREGATE_PATH, new=AsyncMock(return_value="summary")),
        patch(
            f"{ANALYZER_PATH}.analyze_career_priorities",
            new=AsyncMock(return_value=priorities_default),
        ),
        patch(
            f"{ANALYZER_PATH}.generate_milestones",
            new=AsyncMock(return_value=milestones_default),
        ),
        patch(
            f"{ANALYZER_PATH}.generate_recommendations",
            new=AsyncMock(return_value=recs_default),
        ),
        patch(
            f"{ANALYZER_PATH}.clamp_confidence",
            return_value=confidence,
        ),
        patch(
            f"{ANALYZER_PATH}.clamp_impact_score",
            return_value=impact,
        ),
        patch(
            f"{ANALYZER_PATH}.validate_milestone_timeline",
            return_value=validated_date,
        ),
    ]


# ── Dashboard with populated data (lines 183-188, 203-204) ─────────


class TestGetDashboardPopulated:
    @pytest.mark.asyncio
    async def test_plan_summary_includes_milestone_counts(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-dash-1@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.COMPLETED.value,
        )
        await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.NOT_STARTED.value,
            title="Other",
        )
        await db_session.flush()

        result = await get_dashboard(db_session, user_id=user.id)
        assert len(result.active_plans) == 1
        summary = result.active_plans[0]
        assert summary["milestone_count"] == 2
        assert summary["completed_milestone_count"] == 1

    @pytest.mark.asyncio
    async def test_dashboard_recent_recommendations_collected(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-dash-2@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        for i in range(3):
            rec = PlanRecommendation(
                plan_id=str(plan.id),
                source_engine="predictive_career",
                recommendation_type="general",
                title=f"Rec {i}",
                rationale="Why",
                urgency="medium",
                impact_score=40.0,
            )
            db_session.add(rec)
        await db_session.flush()

        result = await get_dashboard(db_session, user_id=user.id)
        assert len(result.recent_recommendations) == 3

    @pytest.mark.asyncio
    async def test_dashboard_filters_active_and_draft_only(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-dash-3@test.com")
        await _make_plan(
            db_session, user=user, dna=dna,
            status=PlanStatus.DRAFT.value, title="Draft One",
        )
        await _make_plan(
            db_session, user=user, dna=dna,
            status=PlanStatus.ACTIVE.value, title="Active One",
        )
        await _make_plan(
            db_session, user=user, dna=dna,
            status=PlanStatus.ARCHIVED.value, title="Archived",
        )
        await db_session.flush()

        result = await get_dashboard(db_session, user_id=user.id)
        titles = {summary["title"] for summary in result.active_plans}
        assert "Draft One" in titles
        assert "Active One" in titles
        assert "Archived" not in titles

    @pytest.mark.asyncio
    async def test_dashboard_returns_preferences_when_exist(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-dash-4@test.com")
        pref = CareerActionPlannerPreference(
            career_dna_id=str(dna.id),
            user_id=str(user.id),
            preferred_sprint_length_weeks=3,
        )
        db_session.add(pref)
        await db_session.flush()

        result = await get_dashboard(db_session, user_id=user.id)
        assert result.preferences is not None
        assert result.preferences.preferred_sprint_length_weeks == 3


# ── generate_plan milestone/rec persistence (340-359, 373-385) ────


class TestGeneratePlanPersistence:
    @pytest.mark.asyncio
    async def test_persists_milestones_from_llm_output(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-gen-m@test.com")
        milestones_llm = {
            "milestones": [
                {
                    "title": "Learn Kubernetes",
                    "description": "Master k8s",
                    "category": "learning",
                    "target_week": 2,
                    "effort_hours": 20,
                    "priority": 8,
                    "evidence_required": "Cert",
                },
                {
                    "title": "Contribute to OSS",
                    "category": "project",
                    "target_week": 3,
                    "effort_hours": 15,
                    "priority": 6,
                },
            ],
        }
        a, b, c, d, e, f, g, h = _analyzer_patches(milestones=milestones_llm)
        with a, b, c, d, e, f, g, h:
            result = await generate_plan(
                db_session,
                user_id=user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                    target_timeline_weeks=4,
                ),
            )
        assert len(result.plan.milestones) == 2
        titles = {m.title for m in result.plan.milestones}
        assert "Learn Kubernetes" in titles
        assert "Contribute to OSS" in titles

    @pytest.mark.asyncio
    async def test_persists_milestones_with_defaults(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-gen-md@test.com")
        milestones_llm = {"milestones": [{}]}  # all defaults
        a, b, c, d, e, f, g, h = _analyzer_patches(milestones=milestones_llm)
        with a, b, c, d, e, f, g, h:
            result = await generate_plan(
                db_session,
                user_id=user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                ),
            )
        assert len(result.plan.milestones) == 1
        milestone = result.plan.milestones[0]
        assert milestone.title == "Unnamed milestone"
        assert milestone.category == "learning"
        assert milestone.effort_hours == 8
        assert milestone.priority == 5

    @pytest.mark.asyncio
    async def test_persists_recommendations_from_llm_output(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-gen-r@test.com")
        recs_llm = {
            "recommendations": [
                {
                    "source_engine": "threat_radar",
                    "recommendation_type": "risk_mitigation",
                    "title": "Reduce automation risk",
                    "rationale": "Your role is 40% automatable",
                    "urgency": "high",
                    "impact_score": 85.0,
                },
                {
                    "source_engine": "salary_intelligence",
                    "recommendation_type": "salary_growth",
                    "title": "Negotiate raise",
                    "rationale": "Market value up 15%",
                    "urgency": "medium",
                    "impact_score": 70.0,
                },
            ],
        }
        a, b, c, d, e, f, g, h = _analyzer_patches(recommendations=recs_llm)
        with a, b, c, d, e, f, g, h:
            result = await generate_plan(
                db_session,
                user_id=user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                ),
            )
        assert len(result.recommendations) == 2
        engines = {r.source_engine for r in result.recommendations}
        assert "threat_radar" in engines
        assert "salary_intelligence" in engines

    @pytest.mark.asyncio
    async def test_persists_recommendations_with_defaults(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-gen-rd@test.com")
        recs_llm = {"recommendations": [{}]}
        a, b, c, d, e, f, g, h = _analyzer_patches(recommendations=recs_llm)
        with a, b, c, d, e, f, g, h:
            result = await generate_plan(
                db_session,
                user_id=user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                ),
            )
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.source_engine == "predictive_career"
        assert rec.recommendation_type == "general"
        assert rec.title == "Unnamed recommendation"
        assert rec.urgency == "medium"

    @pytest.mark.asyncio
    async def test_generate_plan_respects_preferences(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-gen-p@test.com")
        pref = CareerActionPlannerPreference(
            career_dna_id=str(dna.id),
            user_id=str(user.id),
            preferred_sprint_length_weeks=6,
            max_milestones_per_plan=3,
        )
        db_session.add(pref)
        await db_session.flush()

        a, b, c, d, e, f, g, h = _analyzer_patches()
        with a, b, c, d, e, f, g, h:
            result = await generate_plan(
                db_session,
                user_id=user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                    target_timeline_weeks=4,
                ),
            )
        assert "6-Week Sprint" in result.plan.title


# ── get_plan (428-441) ────────────────────────────────────────────


class TestGetPlan:
    @pytest.mark.asyncio
    async def test_returns_plan_with_relationships(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-getp-1@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        result = await get_plan(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=user.id,
        )
        assert result is not None
        assert str(result.id) == str(plan.id)
        assert len(result.milestones) == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-getp-2@test.com")
        result = await get_plan(
            db_session,
            plan_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_mismatch(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-getp-3@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await db_session.flush()

        result = await get_plan(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=uuid.uuid4(),
        )
        assert result is None


# ── update_plan_status (468-482) ──────────────────────────────────


class TestUpdatePlanStatus:
    @pytest.mark.asyncio
    async def test_valid_transition_draft_to_active(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-uste-1@test.com")
        plan = await _make_plan(
            db_session, user=user, dna=dna, status=PlanStatus.DRAFT.value,
        )
        await db_session.flush()

        updated = await update_plan_status(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=user.id,
            new_status=PlanStatus.ACTIVE.value,
        )
        assert updated.status == PlanStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_valid_transition_active_to_paused(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-uste-2@test.com")
        plan = await _make_plan(
            db_session, user=user, dna=dna, status=PlanStatus.ACTIVE.value,
        )
        await db_session.flush()

        updated = await update_plan_status(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=user.id,
            new_status=PlanStatus.PAUSED.value,
        )
        assert updated.status == PlanStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-uste-3@test.com")
        plan = await _make_plan(
            db_session, user=user, dna=dna, status=PlanStatus.DRAFT.value,
        )
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot transition"):
            await update_plan_status(
                db_session,
                plan_id=uuid.UUID(str(plan.id)),
                user_id=user.id,
                new_status=PlanStatus.COMPLETED.value,
            )

    @pytest.mark.asyncio
    async def test_archived_no_transitions_allowed(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-uste-4@test.com")
        plan = await _make_plan(
            db_session, user=user, dna=dna, status=PlanStatus.ARCHIVED.value,
        )
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot transition"):
            await update_plan_status(
                db_session,
                plan_id=uuid.UUID(str(plan.id)),
                user_id=user.id,
                new_status=PlanStatus.ACTIVE.value,
            )

    @pytest.mark.asyncio
    async def test_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-uste-5@test.com")
        with pytest.raises(ValueError, match="Plan not found"):
            await update_plan_status(
                db_session,
                plan_id=uuid.uuid4(),
                user_id=user.id,
                new_status=PlanStatus.ACTIVE.value,
            )


# ── get_milestones (507-510) ──────────────────────────────────────


class TestGetMilestones:
    @pytest.mark.asyncio
    async def test_returns_milestones(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-getms-1@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await _make_milestone(db_session, plan=plan, title="M1")
        await _make_milestone(db_session, plan=plan, title="M2")
        await db_session.flush()

        milestones = await get_milestones(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=user.id,
        )
        assert len(milestones) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_no_milestones(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-getms-2@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await db_session.flush()

        milestones = await get_milestones(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            user_id=user.id,
        )
        assert milestones == []

    @pytest.mark.asyncio
    async def test_plan_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-getms-3@test.com")
        with pytest.raises(ValueError, match="Plan not found"):
            await get_milestones(
                db_session,
                plan_id=uuid.uuid4(),
                user_id=user.id,
            )


# ── update_milestone (536-567) ────────────────────────────────────


class TestUpdateMilestone:
    @pytest.mark.asyncio
    async def test_plan_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-um-1@test.com")
        with pytest.raises(ValueError, match="Plan not found"):
            await update_milestone(
                db_session,
                plan_id=uuid.uuid4(),
                milestone_id=uuid.uuid4(),
                user_id=user.id,
                update_data=UpdateMilestoneRequest(),
            )

    @pytest.mark.asyncio
    async def test_milestone_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-2@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await db_session.flush()

        with pytest.raises(ValueError, match="Milestone not found"):
            await update_milestone(
                db_session,
                plan_id=uuid.UUID(str(plan.id)),
                milestone_id=uuid.uuid4(),
                user_id=user.id,
                update_data=UpdateMilestoneRequest(),
            )

    @pytest.mark.asyncio
    async def test_invalid_status_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-3@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        with pytest.raises(ValueError, match="Invalid status"):
            await update_milestone(
                db_session,
                plan_id=uuid.UUID(str(plan.id)),
                milestone_id=uuid.UUID(str(milestone.id)),
                user_id=user.id,
                update_data=UpdateMilestoneRequest(status="bogus_status"),
            )

    @pytest.mark.asyncio
    async def test_updates_status(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-4@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        updated = await update_milestone(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            update_data=UpdateMilestoneRequest(
                status=MilestoneStatus.IN_PROGRESS.value,
            ),
        )
        assert updated.status == MilestoneStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_updates_target_date(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-5@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        new_date = date.today() + timedelta(days=30)
        updated = await update_milestone(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            update_data=UpdateMilestoneRequest(target_date=new_date),
        )
        assert updated.target_date == new_date

    @pytest.mark.asyncio
    async def test_updates_effort_hours(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-6@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        updated = await update_milestone(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            update_data=UpdateMilestoneRequest(effort_hours=25),
        )
        assert updated.effort_hours == 25

    @pytest.mark.asyncio
    async def test_updates_priority(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-7@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan, priority=3)
        await db_session.flush()

        updated = await update_milestone(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            update_data=UpdateMilestoneRequest(priority=9),
        )
        assert updated.priority == 9

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-um-8@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        new_date = date.today() + timedelta(days=14)
        updated = await update_milestone(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            update_data=UpdateMilestoneRequest(
                status=MilestoneStatus.COMPLETED.value,
                target_date=new_date,
                effort_hours=40,
                priority=10,
            ),
        )
        assert updated.status == MilestoneStatus.COMPLETED.value
        assert updated.target_date == new_date
        assert updated.effort_hours == 40
        assert updated.priority == 10


# ── log_progress (596-630) ────────────────────────────────────────


class TestLogProgress:
    @pytest.mark.asyncio
    async def test_plan_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-lp-1@test.com")
        with pytest.raises(ValueError, match="Plan not found"):
            await log_progress(
                db_session,
                plan_id=uuid.uuid4(),
                milestone_id=uuid.uuid4(),
                user_id=user.id,
                progress_data=LogProgressRequest(progress_percent=50.0),
            )

    @pytest.mark.asyncio
    async def test_milestone_not_found_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-2@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        await db_session.flush()

        with pytest.raises(ValueError, match="Milestone not found"):
            await log_progress(
                db_session,
                plan_id=uuid.UUID(str(plan.id)),
                milestone_id=uuid.uuid4(),
                user_id=user.id,
                progress_data=LogProgressRequest(progress_percent=50.0),
            )

    @pytest.mark.asyncio
    async def test_creates_progress_entry(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-3@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(db_session, plan=plan)
        await db_session.flush()

        entry = await log_progress(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            progress_data=LogProgressRequest(
                progress_percent=45.0,
                notes="Halfway there",
                evidence_url="https://example.com/proof",
            ),
        )
        assert entry.progress_percent == 45.0
        assert entry.notes == "Halfway there"
        assert entry.evidence_url == "https://example.com/proof"

    @pytest.mark.asyncio
    async def test_100_percent_marks_completed(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-4@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.IN_PROGRESS.value,
        )
        await db_session.flush()

        await log_progress(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            progress_data=LogProgressRequest(progress_percent=100.0),
        )
        await db_session.refresh(milestone)
        assert milestone.status == MilestoneStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_partial_progress_from_not_started_goes_in_progress(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-5@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.NOT_STARTED.value,
        )
        await db_session.flush()

        await log_progress(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            progress_data=LogProgressRequest(progress_percent=20.0),
        )
        await db_session.refresh(milestone)
        assert milestone.status == MilestoneStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_zero_percent_leaves_status_unchanged(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-6@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.NOT_STARTED.value,
        )
        await db_session.flush()

        await log_progress(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            progress_data=LogProgressRequest(progress_percent=0.0),
        )
        await db_session.refresh(milestone)
        assert milestone.status == MilestoneStatus.NOT_STARTED.value

    @pytest.mark.asyncio
    async def test_partial_on_in_progress_milestone_preserved(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-lp-7@test.com")
        plan = await _make_plan(db_session, user=user, dna=dna)
        milestone = await _make_milestone(
            db_session, plan=plan,
            status=MilestoneStatus.IN_PROGRESS.value,
        )
        await db_session.flush()

        await log_progress(
            db_session,
            plan_id=uuid.UUID(str(plan.id)),
            milestone_id=uuid.UUID(str(milestone.id)),
            user_id=user.id,
            progress_data=LogProgressRequest(progress_percent=65.0),
        )
        await db_session.refresh(milestone)
        assert milestone.status == MilestoneStatus.IN_PROGRESS.value


# ── Preferences update all fields (705-713) ────────────────────────


class TestPreferencesFullUpdate:
    @pytest.mark.asyncio
    async def test_update_sets_max_milestones(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-mm@test.com")
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                max_milestones_per_plan=8,
            ),
        )
        assert pref.max_milestones_per_plan == 8

    @pytest.mark.asyncio
    async def test_update_sets_focus_areas(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-fa@test.com")
        areas = {"topics": ["cloud", "ml"]}
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                focus_areas=areas,
            ),
        )
        assert pref.focus_areas == areas

    @pytest.mark.asyncio
    async def test_update_sets_notification_frequency(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-nf@test.com")
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                notification_frequency="daily",
            ),
        )
        assert pref.notification_frequency == "daily"

    @pytest.mark.asyncio
    async def test_update_sets_auto_generate_recommendations(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-ag@test.com")
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                auto_generate_recommendations=False,
            ),
        )
        assert pref.auto_generate_recommendations is False

    @pytest.mark.asyncio
    async def test_update_sets_all_fields_together(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-all@test.com")
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                preferred_sprint_length_weeks=4,
                max_milestones_per_plan=7,
                focus_areas={"t": ["x"]},
                notification_frequency="biweekly",
                auto_generate_recommendations=True,
            ),
        )
        assert pref.preferred_sprint_length_weeks == 4
        assert pref.max_milestones_per_plan == 7
        assert pref.focus_areas == {"t": ["x"]}
        assert pref.notification_frequency == "biweekly"
        assert pref.auto_generate_recommendations is True

    @pytest.mark.asyncio
    async def test_get_preferences_returns_existing(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="cap-pref-get@test.com")
        pref = CareerActionPlannerPreference(
            career_dna_id=str(dna.id),
            user_id=str(user.id),
            preferred_sprint_length_weeks=5,
        )
        db_session.add(pref)
        await db_session.flush()

        result = await get_preferences(db_session, user_id=user.id)
        assert result is not None
        assert result.preferred_sprint_length_weeks == 5

    @pytest.mark.asyncio
    async def test_update_second_call_modifies_existing_record(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cap-pref-2@test.com")
        first = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                preferred_sprint_length_weeks=2,
            ),
        )
        second = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerActionPlannerPreferenceUpdate(
                preferred_sprint_length_weeks=8,
            ),
        )
        assert first.id == second.id
        assert second.preferred_sprint_length_weeks == 8
