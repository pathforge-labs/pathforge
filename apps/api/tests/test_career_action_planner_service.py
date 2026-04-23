"""
PathForge — Career Action Planner Service Unit Tests
=====================================================
Service-layer tests for career_action_planner_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_action_planner import PlanType
from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.user import User
from app.schemas.career_action_planner import (
    CareerActionPlannerPreferenceUpdate,
    GeneratePlanRequest,
)
from app.services.career_action_planner_service import (
    _format_skills_for_prompt,
    _get_skill_names,
    generate_plan,
    get_dashboard,
    get_preferences,
    update_preferences,
)

# ── Fixtures ──────────────────────────────────────────────────────


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
        full_name="Planner Tester",
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


# ── Pure helpers ──────────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_no_skills_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_formats_skills_with_proficiency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Rust",
            category="technical",
            proficiency_level="expert",
            confidence=0.95,
            source="resume",
        )
        dna.skill_genome = [skill]
        result = _format_skills_for_prompt(dna)
        assert "Rust" in result
        assert "expert" in result


class TestGetSkillNames:
    def test_returns_empty_list_when_no_skills(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _get_skill_names(dna) == []

    def test_returns_skill_names(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Python",
                category="technical",
                proficiency_level="expert",
                confidence=0.9,
                source="resume",
            ),
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Docker",
                category="devops",
                proficiency_level="advanced",
                confidence=0.8,
                source="resume",
            ),
        ]
        names = _get_skill_names(dna)
        assert "Python" in names
        assert "Docker" in names


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_result_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result.active_plans == []
        assert result.preferences is None

    @pytest.mark.asyncio
    async def test_returns_empty_plans_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="cap-dash@test.com")
        result = await get_dashboard(db_session, user_id=_user.id)
        assert result.active_plans == []


# ── generate_plan ─────────────────────────────────────────────────


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_raises_for_invalid_plan_type(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="cap-invalid@test.com")
        request = GeneratePlanRequest(plan_type="invalid_type")
        with pytest.raises(ValueError, match="Invalid plan type"):
            await generate_plan(db_session, user_id=_user.id, request_data=request)

    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        request = GeneratePlanRequest(plan_type=PlanType.SKILL_DEVELOPMENT.value)
        with pytest.raises(ValueError, match="Career DNA"):
            await generate_plan(db_session, user_id=uuid.uuid4(), request_data=request)

    @pytest.mark.asyncio
    async def test_happy_path_persists_plan(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="cap-gen@test.com")

        fake_priorities = {
            "overall_assessment": "Focus on cloud skills",
            "priorities": [],
            "confidence": 0.8,
        }
        fake_milestones = {"milestones": []}
        fake_recs = {"recommendations": []}

        context_mock = MagicMock(return_value={
            "primary_role": "Engineer",
            "primary_industry": "Tech",
            "seniority_level": "mid",
            "location": "Utrecht",
            "skills": ["Python"],
        })

        with (
            patch(
                "app.services.career_action_planner_service"
                ".CareerActionPlannerAnalyzer.build_priority_context",
                context_mock,
            ),
            patch(
                "app.services.career_action_planner_service"
                ".aggregate_intelligence",
                new=AsyncMock(return_value="summary"),
            ),
            patch(
                "app.services.career_action_planner_service"
                ".CareerActionPlannerAnalyzer.analyze_career_priorities",
                new=AsyncMock(return_value=fake_priorities),
            ),
            patch(
                "app.services.career_action_planner_service"
                ".CareerActionPlannerAnalyzer.generate_milestones",
                new=AsyncMock(return_value=fake_milestones),
            ),
            patch(
                "app.services.career_action_planner_service"
                ".CareerActionPlannerAnalyzer.generate_recommendations",
                new=AsyncMock(return_value=fake_recs),
            ),
            patch(
                "app.services.career_action_planner_service"
                ".CareerActionPlannerAnalyzer.clamp_confidence",
                return_value=0.8,
            ),
        ):
            result = await generate_plan(
                db_session,
                user_id=_user.id,
                request_data=GeneratePlanRequest(
                    plan_type=PlanType.SKILL_DEVELOPMENT.value,
                    target_timeline_weeks=4,
                ),
            )

        assert result.plan.id is not None
        assert result.plan.plan_type == PlanType.SKILL_DEVELOPMENT.value


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(db_session, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        update = CareerActionPlannerPreferenceUpdate()
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=update,
            )

    @pytest.mark.asyncio
    async def test_update_preferences_creates_record(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="cap-pref@test.com")
        update = CareerActionPlannerPreferenceUpdate(
            preferred_sprint_length_weeks=6,
        )
        pref = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        assert pref is not None
        assert pref.preferred_sprint_length_weeks == 6

    @pytest.mark.asyncio
    async def test_update_preferences_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="cap-pref-idem@test.com")
        update = CareerActionPlannerPreferenceUpdate()
        pref1 = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        pref2 = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        assert pref1.id == pref2.id
