"""
PathForge — Collective Intelligence Service Unit Tests
======================================================
Service-layer tests for collective_intelligence_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.collective_intelligence import CollectiveIntelligencePreference
from app.models.user import User
from app.services.collective_intelligence_service import (
    _format_skills_for_prompt,
    _get_skills_count,
    _get_years_experience,
    get_ci_dashboard,
    get_industry_snapshot,
    get_or_update_preferences,
    get_salary_benchmark,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 2,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="CI Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Data Engineer",
        primary_industry="Technology",
        seniority_level="senior",
        location="Amsterdam",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        for i in range(skill_count):
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=f"Skill{i}",
                category="technical",
                proficiency_level="advanced",
                confidence=0.8,
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

    def test_formats_skills_correctly(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Python",
            category="technical",
            proficiency_level="expert",
            confidence=0.9,
            source="resume",
        )
        dna.skill_genome = [skill]
        result = _format_skills_for_prompt(dna)
        assert "Python" in result
        assert "expert" in result


class TestGetYearsExperience:
    def test_returns_default_when_no_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.experience_blueprint = None
        assert _get_years_experience(dna) == 3

    def test_returns_default_when_blueprint_is_missing_total_years(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # experience_blueprint is a relationship — leave as None triggers default
        assert _get_years_experience(dna) == 3


class TestGetSkillsCount:
    def test_returns_zero_when_no_skills(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _get_skills_count(dna) == 0

    def test_returns_correct_count(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name=f"S{i}",
                category="technical",
                proficiency_level="advanced",
                confidence=0.8,
                source="resume",
            )
            for i in range(4)
        ]
        assert _get_skills_count(dna) == 4


# ── get_ci_dashboard ──────────────────────────────────────────────


class TestGetCIDashboard:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_ci_dashboard(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_empty_collections_when_no_data(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-dash@test.com")
        result = await get_ci_dashboard(db_session, user_id=_user.id)

        assert result["industry_snapshots"] == []
        assert result["salary_benchmarks"] == []
        assert result["peer_cohort_analyses"] == []
        assert result["latest_pulse"] is None
        assert result["preferences"] is None


# ── get_industry_snapshot ─────────────────────────────────────────


class TestGetIndustrySnapshot:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_industry_snapshot(
                db_session,
                user_id=uuid.uuid4(),
                industry="Technology",
                region="Netherlands",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_snapshot(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-snap@test.com")

        fake_result = {
            "trend_direction": "growing",
            "demand_intensity": "high",
            "top_emerging_skills": ["AI", "MLOps"],
            "confidence": 0.85,
        }

        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=AsyncMock(return_value=fake_result),
        ):
            snapshot = await get_industry_snapshot(
                db_session,
                user_id=_user.id,
                industry="Technology",
                region="Netherlands",
            )

        assert snapshot.id is not None
        assert snapshot.industry == "Technology"
        assert snapshot.trend_direction == "growing"
        assert snapshot.confidence_score == 0.85


# ── get_salary_benchmark ──────────────────────────────────────────


class TestGetSalaryBenchmark:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_salary_benchmark(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_happy_path_persists_benchmark(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-bench@test.com")

        fake_result = {
            "benchmark_min": 60000.0,
            "benchmark_median": 80000.0,
            "benchmark_max": 100000.0,
            "user_percentile": 70.0,
            "confidence": 0.78,
        }

        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_salary_benchmark",
            new=AsyncMock(return_value=fake_result),
        ):
            benchmark = await get_salary_benchmark(
                db_session, user_id=_user.id, currency="EUR",
            )

        assert benchmark.id is not None
        assert benchmark.benchmark_median == 80000.0
        assert benchmark.currency == "EUR"


# ── get_or_update_preferences ─────────────────────────────────────


class TestGetOrUpdatePreferences:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_or_update_preferences(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_creates_preferences_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-pref-create@test.com")
        pref = await get_or_update_preferences(db_session, user_id=_user.id)
        assert pref is not None
        assert pref.id is not None

    @pytest.mark.asyncio
    async def test_update_sets_allowed_field(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-pref-update@test.com")
        pref = await get_or_update_preferences(
            db_session,
            user_id=_user.id,
            updates={"preferred_currency": "USD"},
        )
        assert pref.preferred_currency == "USD"

    @pytest.mark.asyncio
    async def test_idempotent_get(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ci-pref-idem@test.com")
        pref1 = await get_or_update_preferences(db_session, user_id=_user.id)
        pref2 = await get_or_update_preferences(db_session, user_id=_user.id)
        assert pref1.id == pref2.id

    @pytest.mark.asyncio
    async def test_create_preference_directly_via_db(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="ci-pref-direct@test.com",
        )
        pref = CollectiveIntelligencePreference(
            career_dna_id=str(_dna.id),
            user_id=str(_user.id),
        )
        db_session.add(pref)
        await db_session.flush()
        assert pref.id is not None
