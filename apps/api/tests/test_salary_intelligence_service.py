"""
PathForge — Salary Intelligence Service Unit Tests
====================================================
Service-layer tests for salary_intelligence_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.

Coverage targets:
    - Pure helpers: _format_skills_for_salary, _format_experience_summary,
      _get_industry_context, _get_role_title, _get_location,
      _estimate_seniority_level, _estimate_years_of_experience,
      _extract_skill_names
    - SalaryIntelligenceService.run_full_scan (happy path, no CareerDNA,
      no skills, no estimate returned)
    - SalaryIntelligenceService.get_dashboard
    - SalaryIntelligenceService.get_salary_estimate
    - SalaryIntelligenceService.get_skill_impacts
    - SalaryIntelligenceService.get_salary_trajectory
    - SalaryIntelligenceService.run_scenario
    - SalaryIntelligenceService.get_scenarios
    - SalaryIntelligenceService.get_preferences / update_preferences
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, ExperienceBlueprint, SkillGenomeEntry
from app.models.salary_intelligence import SalaryEstimate
from app.models.user import User
from app.services.salary_intelligence_service import (
    SalaryIntelligenceService,
    _estimate_seniority_level,
    _estimate_years_of_experience,
    _extract_skill_names,
    _format_experience_summary,
    _format_skills_for_salary,
    _get_industry_context,
    _get_location,
    _get_role_title,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    with_blueprint: bool = False,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Salary Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Data Engineer",
        primary_industry="Finance",
        seniority_level="mid",
        location="Berlin",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        for name in ["Python", "SQL"]:
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=name,
                category="technical",
                proficiency_level="advanced",
                confidence=0.85,
                years_experience=3,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    if with_blueprint:
        bp = ExperienceBlueprint(
            career_dna_id=dna.id,
            total_years=5.0,
            career_direction="accelerating",
        )
        db.add(bp)
        await db.flush()

    return user, dna


# ── Pure helper tests ─────────────────────────────────────────────


class TestPureHelpers:
    def _dna(self) -> CareerDNA:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        dna.experience_blueprint = None
        return dna

    def test_format_skills_no_genome(self) -> None:
        dna = self._dna()
        assert _format_skills_for_salary(dna) == "No skills data available"

    def test_format_skills_with_entries(self) -> None:
        dna = self._dna()
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Rust",
            category="systems",
            proficiency_level="intermediate",
            confidence=0.75,
            source="resume",
        )
        dna.skill_genome = [entry]
        result = _format_skills_for_salary(dna)
        assert "Rust" in result
        assert "intermediate" in result

    def test_format_experience_summary_no_blueprint(self) -> None:
        dna = self._dna()
        result = _format_experience_summary(dna)
        assert result == "No experience data available"

    def test_format_experience_summary_with_blueprint(self) -> None:
        dna = self._dna()
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=7.0,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        result = _format_experience_summary(dna)
        assert "7" in result

    def test_get_industry_context_uses_primary(self) -> None:
        dna = self._dna()
        dna.primary_industry = "Healthcare"
        assert _get_industry_context(dna) == "Healthcare"

    def test_get_industry_context_defaults_to_technology(self) -> None:
        dna = self._dna()
        dna.primary_industry = None
        assert _get_industry_context(dna) == "Technology"

    def test_get_role_title_uses_primary(self) -> None:
        dna = self._dna()
        dna.primary_role = "ML Engineer"
        assert _get_role_title(dna) == "ML Engineer"

    def test_get_role_title_defaults_to_software_engineer(self) -> None:
        dna = self._dna()
        dna.primary_role = None
        assert _get_role_title(dna) == "Software Engineer"

    def test_get_location_uses_primary(self) -> None:
        dna = self._dna()
        dna.location = "Dublin"
        assert _get_location(dna) == "Dublin"

    def test_get_location_defaults_to_netherlands(self) -> None:
        dna = self._dna()
        dna.location = None
        assert _get_location(dna) == "Netherlands"

    def test_estimate_seniority_from_field(self) -> None:
        dna = self._dna()
        dna.seniority_level = "staff"
        assert _estimate_seniority_level(dna) == "staff"

    def test_estimate_seniority_from_blueprint_junior(self) -> None:
        dna = self._dna()
        dna.seniority_level = None
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=2.0,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        assert _estimate_seniority_level(dna) == "junior"

    def test_estimate_seniority_from_blueprint_senior(self) -> None:
        dna = self._dna()
        dna.seniority_level = None
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=8.0,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        assert _estimate_seniority_level(dna) == "senior"

    def test_estimate_seniority_from_blueprint_staff(self) -> None:
        dna = self._dna()
        dna.seniority_level = None
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=12.0,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        assert _estimate_seniority_level(dna) == "staff"

    def test_estimate_seniority_no_blueprint_defaults_to_mid(self) -> None:
        dna = self._dna()
        dna.seniority_level = None
        assert _estimate_seniority_level(dna) == "mid"

    def test_estimate_years_from_blueprint(self) -> None:
        dna = self._dna()
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=6.9,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        assert _estimate_years_of_experience(dna) == 6

    def test_estimate_years_no_blueprint_defaults_to_five(self) -> None:
        dna = self._dna()
        assert _estimate_years_of_experience(dna) == 5

    def test_extract_skill_names_empty(self) -> None:
        dna = self._dna()
        assert _extract_skill_names(dna) == []

    def test_extract_skill_names_returns_names(self) -> None:
        dna = self._dna()
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Go",
            category="technical",
            proficiency_level="intermediate",
            confidence=0.8,
            source="resume",
        )
        dna.skill_genome = [entry]
        names = _extract_skill_names(dna)
        assert names == ["Go"]


# ── run_full_scan ─────────────────────────────────────────────────


class TestRunFullScan:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.run_full_scan(
            db_session, user_id=uuid.uuid4()
        )
        assert result["status"] == "error"
        assert "Career DNA" in result["detail"]

    @pytest.mark.asyncio
    async def test_returns_error_when_no_skills(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="scan-noskills@test.com", with_skills=False,
        )
        result = await SalaryIntelligenceService.run_full_scan(
            db_session, user_id=_user.id,
        )
        assert result["status"] == "error"
        assert "No skills" in result["detail"]

    @pytest.mark.asyncio
    async def test_happy_path_creates_estimate_and_impacts(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="scan-happy@test.com")

        fake_estimate: dict[str, Any] = {
            "estimated_min": 60000.0,
            "estimated_max": 90000.0,
            "estimated_median": 72000.0,
            "confidence": 0.78,
            "data_points_count": 120,
            "market_percentile": 65.0,
        }
        fake_impacts: list[dict[str, Any]] = [
            {
                "skill_name": "Python",
                "category": "technical",
                "salary_impact_amount": 5000.0,
                "salary_impact_percent": 7.0,
                "demand_premium": 0.8,
                "scarcity_factor": 0.6,
                "impact_direction": "positive",
            }
        ]

        with (
            patch(
                "app.services.salary_intelligence_service"
                ".SalaryIntelligenceAnalyzer.analyze_salary_range",
                new=AsyncMock(return_value=fake_estimate),
            ),
            patch(
                "app.services.salary_intelligence_service"
                ".SalaryIntelligenceAnalyzer.analyze_skill_impacts",
                new=AsyncMock(return_value=fake_impacts),
            ),
        ):
            result = await SalaryIntelligenceService.run_full_scan(
                db_session, user_id=_user.id,
            )

        assert result["status"] == "completed"
        assert result["estimate"] is not None
        assert result["estimate"].estimated_median == 72000.0
        assert len(result["skill_impacts"]) == 1
        assert result["history_entry_created"] is True

    @pytest.mark.asyncio
    async def test_handles_none_estimate_from_llm(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="scan-noestimate@test.com"
        )
        with patch(
            "app.services.salary_intelligence_service"
            ".SalaryIntelligenceAnalyzer.analyze_salary_range",
            new=AsyncMock(return_value=None),
        ):
            result = await SalaryIntelligenceService.run_full_scan(
                db_session, user_id=_user.id,
            )

        assert result["status"] == "completed"
        assert result["estimate"] is None
        assert result["history_entry_created"] is False


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_state_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_dashboard(
            db_session, user_id=uuid.uuid4()
        )
        assert result["estimate"] is None
        assert result["skill_impacts"] == []
        assert result["trajectory"] is None
        assert result["recent_scenarios"] == []

    @pytest.mark.asyncio
    async def test_returns_populated_state_with_data(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="dashboard-data@test.com"
        )
        estimate = SalaryEstimate(
            career_dna_id=_dna.id,
            role_title="Data Engineer",
            location="Berlin",
            seniority_level="mid",
            industry="Finance",
            estimated_min=55000.0,
            estimated_max=80000.0,
            estimated_median=65000.0,
            currency="EUR",
            confidence=0.72,
            data_points_count=100,
        )
        db_session.add(estimate)
        await db_session.flush()

        result = await SalaryIntelligenceService.get_dashboard(
            db_session, user_id=_user.id
        )
        assert result["estimate"] is not None
        assert result["estimate"].estimated_median == 65000.0
        assert result["last_scan_at"] is not None


# ── Individual accessors ──────────────────────────────────────────


class TestIndividualAccessors:
    @pytest.mark.asyncio
    async def test_get_salary_estimate_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_salary_estimate(
            db_session, user_id=uuid.uuid4()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_skill_impacts_no_career_dna_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_skill_impacts(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_salary_trajectory_no_career_dna_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_salary_trajectory(
            db_session, user_id=uuid.uuid4()
        )
        assert result == {"history": []}

    @pytest.mark.asyncio
    async def test_get_scenarios_no_career_dna_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_scenarios(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_scenario_by_id_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_scenario_by_id(
            db_session, user_id=uuid.uuid4(), scenario_id=uuid.uuid4()
        )
        assert result is None


# ── run_scenario ──────────────────────────────────────────────────


class TestRunScenario:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.run_scenario(
            db_session,
            user_id=uuid.uuid4(),
            scenario_type="skill_addition",
            scenario_label="Add Kubernetes",
            scenario_input={"skill": "Kubernetes"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_current_estimate(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="scenario-noest@test.com"
        )
        result = await SalaryIntelligenceService.run_scenario(
            db_session,
            user_id=_user.id,
            scenario_type="skill_addition",
            scenario_label="Add Kubernetes",
            scenario_input={"skill": "Kubernetes"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_persists_scenario_on_success(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="scenario-ok@test.com")
        estimate = SalaryEstimate(
            career_dna_id=_dna.id,
            role_title="Data Engineer",
            location="Berlin",
            seniority_level="mid",
            industry="Finance",
            estimated_min=55000.0,
            estimated_max=80000.0,
            estimated_median=65000.0,
            currency="EUR",
            confidence=0.72,
            data_points_count=100,
        )
        db_session.add(estimate)
        await db_session.flush()

        fake_result: dict[str, Any] = {
            "projected_min": 60000.0,
            "projected_max": 85000.0,
            "projected_median": 70000.0,
            "delta_amount": 5000.0,
            "delta_percent": 7.7,
            "confidence": 0.65,
        }
        with patch(
            "app.services.salary_intelligence_service"
            ".SalaryIntelligenceAnalyzer.simulate_scenario",
            new=AsyncMock(return_value=fake_result),
        ):
            scenario = await SalaryIntelligenceService.run_scenario(
                db_session,
                user_id=_user.id,
                scenario_type="skill_addition",
                scenario_label="Add Kubernetes",
                scenario_input={"skill": "Kubernetes"},
            )

        assert scenario is not None
        assert scenario.projected_median == 70000.0
        assert scenario.delta_percent == 7.7


# ── Preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SalaryIntelligenceService.get_preferences(
            db_session, user_id=uuid.uuid4()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_no_career_dna_raises(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await SalaryIntelligenceService.update_preferences(
                db_session, user_id=uuid.uuid4(), updates={}
            )

    @pytest.mark.asyncio
    async def test_update_preferences_creates_and_updates(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="prefs-salary@test.com"
        )
        pref = await SalaryIntelligenceService.update_preferences(
            db_session,
            user_id=_user.id,
            updates={"preferred_currency": "USD"},
        )
        assert pref.preferred_currency == "USD"
