"""
PathForge — Predictive Career Service Unit Tests
==================================================
Service-layer tests for predictive_career_service.py.
All LLM analyzer calls are mocked; database uses the in-memory
SQLite fixture so ORM query paths are exercised.

Coverage targets:
    - _format_skills_for_prompt (both branches)
    - _get_years_experience (both branches)
    - scan_emerging_roles (happy path + no CareerDNA)
    - get_disruption_forecasts (happy path + no CareerDNA)
    - get_opportunity_surfaces (happy path + no CareerDNA)
    - get_career_forecast (happy path + no CareerDNA)
    - get_pc_dashboard (with and without data)
    - run_predictive_scan (happy path + no CareerDNA)
    - get_or_update_preferences (create, update, no CareerDNA)
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, ExperienceBlueprint, SkillGenomeEntry
from app.models.user import User
from app.services.predictive_career_service import (
    _format_skills_for_prompt,
    _get_years_experience,
    get_career_forecast,
    get_disruption_forecasts,
    get_opportunity_surfaces,
    get_or_update_preferences,
    get_pc_dashboard,
    run_predictive_scan,
    scan_emerging_roles,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_user_and_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    with_blueprint: bool = False,
) -> tuple[User, CareerDNA]:
    """Create a minimal User + CareerDNA in the test database."""
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Test User",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="senior",
        location="Amsterdam",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        skill = SkillGenomeEntry(
            career_dna_id=dna.id,
            skill_name="Python",
            category="technical",
            proficiency_level="expert",
            confidence=0.9,
            years_experience=5,
            source="resume",
        )
        db.add(skill)
        await db.flush()

    if with_blueprint:
        bp = ExperienceBlueprint(
            career_dna_id=dna.id,
            total_years=8.0,
            career_direction="accelerating",
        )
        db.add(bp)
        await db.flush()

    return user, dna


# ── Pure helper tests ─────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_empty_genome_returns_no_skills_message(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        result = _format_skills_for_prompt(dna)
        assert result == "No skills recorded"

    def test_skills_formatted_correctly(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Python",
            category="technical",
            proficiency_level="expert",
            confidence=0.9,
            source="resume",
        )
        dna.skill_genome = [entry]
        result = _format_skills_for_prompt(dna)
        assert "Python" in result
        assert "expert" in result


class TestGetYearsExperience:
    def test_no_blueprint_returns_default(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.experience_blueprint = None
        assert _get_years_experience(dna) == 3

    def test_blueprint_with_total_years(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=7.5,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        result = _get_years_experience(dna)
        assert result == 7

    def test_blueprint_with_zero_years_returns_minimum_one(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        bp = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=0.0,
            career_direction="accelerating",
        )
        dna.experience_blueprint = bp
        assert _get_years_experience(dna) >= 1


# ── scan_emerging_roles ──────────────────────────────────────────


class TestScanEmergingRoles:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await scan_emerging_roles(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_persists_and_returns_roles(self, db_session: AsyncSession) -> None:
        _user, _dna = await _make_user_and_dna(db_session, email="scan-roles@test.com")

        fake_roles: list[dict[str, Any]] = [
            {
                "role_title": "AI Product Manager",
                "industry": "Technology",
                "emergence_stage": "growing",
                "growth_rate_pct": 35.0,
                "skill_overlap_pct": 70.0,
                "confidence": 0.8,
            }
        ]
        with patch(
            "app.services.predictive_career_service.PredictiveCareerAnalyzer"
            ".analyze_emerging_roles",
            new=AsyncMock(return_value=fake_roles),
        ):
            roles = await scan_emerging_roles(db_session, user_id=_user.id)

        assert len(roles) == 1
        assert roles[0].role_title == "AI Product Manager"
        assert roles[0].skill_overlap_pct == 70.0

    @pytest.mark.asyncio
    async def test_uses_overrides_when_industry_and_region_provided(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="scan-override@test.com"
        )
        with patch(
            "app.services.predictive_career_service.PredictiveCareerAnalyzer"
            ".analyze_emerging_roles",
            new=AsyncMock(return_value=[]),
        ) as mock_analyze:
            await scan_emerging_roles(
                db_session,
                user_id=_user.id,
                industry="Finance",
                region="London",
            )
        call_kwargs = mock_analyze.call_args.kwargs
        assert call_kwargs["industry"] == "Finance"
        assert call_kwargs["region"] == "London"


# ── get_disruption_forecasts ─────────────────────────────────────


class TestGetDisruptionForecasts:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_disruption_forecasts(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_persists_and_returns_forecasts(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="disruption@test.com"
        )
        fake_forecasts: list[dict[str, Any]] = [
            {
                "disruption_title": "AI Automation Wave",
                "disruption_type": "automation",
                "industry": "Technology",
                "severity_score": 68.0,
                "timeline_months": 18,
                "confidence": 0.75,
            }
        ]
        with patch(
            "app.services.predictive_career_service.PredictiveCareerAnalyzer"
            ".forecast_disruptions",
            new=AsyncMock(return_value=fake_forecasts),
        ):
            forecasts = await get_disruption_forecasts(
                db_session, user_id=_user.id
            )

        assert len(forecasts) == 1
        assert forecasts[0].disruption_title == "AI Automation Wave"
        assert forecasts[0].severity_score == 68.0


# ── get_opportunity_surfaces ─────────────────────────────────────


class TestGetOpportunitySurfaces:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_opportunity_surfaces(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_persists_and_returns_opportunities(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="opportunity@test.com"
        )
        fake_opps: list[dict[str, Any]] = [
            {
                "opportunity_title": "Fractional CTO",
                "opportunity_type": "emerging_role",
                "source_signal": "market_analysis",
                "relevance_score": 85.0,
                "confidence": 0.72,
            }
        ]
        with patch(
            "app.services.predictive_career_service.PredictiveCareerAnalyzer"
            ".surface_opportunities",
            new=AsyncMock(return_value=fake_opps),
        ):
            opps = await get_opportunity_surfaces(db_session, user_id=_user.id)

        assert len(opps) == 1
        assert opps[0].opportunity_title == "Fractional CTO"
        assert opps[0].relevance_score == 85.0


# ── get_career_forecast ──────────────────────────────────────────


class TestGetCareerForecast:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_career_forecast(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_persists_and_returns_forecast(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="forecast@test.com"
        )
        fake_result: dict[str, Any] = {
            "outlook_score": 74.0,
            "outlook_category": "favorable",
            "forecast_horizon_months": 12,
            "role_component": 80.0,
            "disruption_component": 60.0,
            "opportunity_component": 70.0,
            "trend_component": 75.0,
            "confidence": 0.68,
        }
        with patch(
            "app.services.predictive_career_service.PredictiveCareerAnalyzer"
            ".compute_career_forecast",
            new=AsyncMock(return_value=fake_result),
        ):
            forecast = await get_career_forecast(
                db_session,
                user_id=_user.id,
                emerging_roles_count=2,
                disruptions_count=1,
                opportunities_count=3,
            )

        assert forecast.outlook_score == 74.0
        assert forecast.outlook_category == "favorable"
        assert forecast.id is not None


# ── get_pc_dashboard ─────────────────────────────────────────────


class TestGetPcDashboard:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_pc_dashboard(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_empty_collections_when_no_data(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="dashboard-empty@test.com"
        )
        result = await get_pc_dashboard(db_session, user_id=_user.id)

        assert result["latest_forecast"] is None
        assert result["emerging_roles"] == []
        assert result["disruption_forecasts"] == []
        assert result["opportunity_surfaces"] == []
        assert result["preferences"] is None


# ── run_predictive_scan ──────────────────────────────────────────


class TestRunPredictiveScan:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await run_predictive_scan(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_all_sections(self, db_session: AsyncSession) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="full-scan@test.com"
        )
        with (
            patch(
                "app.services.predictive_career_service.PredictiveCareerAnalyzer"
                ".analyze_emerging_roles",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.predictive_career_service.PredictiveCareerAnalyzer"
                ".forecast_disruptions",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.predictive_career_service.PredictiveCareerAnalyzer"
                ".surface_opportunities",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.predictive_career_service.PredictiveCareerAnalyzer"
                ".compute_career_forecast",
                new=AsyncMock(
                    return_value={
                        "outlook_score": 65.0,
                        "outlook_category": "moderate",
                        "confidence": 0.7,
                    }
                ),
            ),
        ):
            result = await run_predictive_scan(db_session, user_id=_user.id)

        assert "career_forecast" in result
        assert "emerging_roles" in result
        assert "disruption_forecasts" in result
        assert "opportunity_surfaces" in result
        assert result["career_forecast"].outlook_score == 65.0


# ── get_or_update_preferences ────────────────────────────────────


class TestGetOrUpdatePreferences:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_or_update_preferences(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_creates_preference_on_first_call(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="prefs-create@test.com"
        )
        pref = await get_or_update_preferences(db_session, user_id=_user.id)
        assert pref is not None
        assert pref.id is not None

    @pytest.mark.asyncio
    async def test_returns_existing_preference_on_second_call(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="prefs-existing@test.com"
        )
        pref1 = await get_or_update_preferences(db_session, user_id=_user.id)
        pref2 = await get_or_update_preferences(db_session, user_id=_user.id)
        assert pref1.id == pref2.id

    @pytest.mark.asyncio
    async def test_applies_allowed_updates(self, db_session: AsyncSession) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="prefs-update@test.com"
        )
        pref = await get_or_update_preferences(
            db_session,
            user_id=_user.id,
            updates={"forecast_horizon_months": 24, "risk_tolerance": "aggressive"},
        )
        assert pref.forecast_horizon_months == 24
        assert pref.risk_tolerance == "aggressive"

    @pytest.mark.asyncio
    async def test_ignores_non_allowed_field_updates(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="prefs-ignore@test.com"
        )
        pref = await get_or_update_preferences(
            db_session,
            user_id=_user.id,
            updates={"nonexistent_field": "value"},
        )
        assert pref is not None

    @pytest.mark.asyncio
    async def test_converts_list_to_dict_for_json_fields(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_user_and_dna(
            db_session, email="prefs-list@test.com"
        )
        pref = await get_or_update_preferences(
            db_session,
            user_id=_user.id,
            updates={"focus_industries": ["Technology", "Finance"]},
        )
        assert isinstance(pref.focus_industries, dict)
        assert pref.focus_industries["items"] == ["Technology", "Finance"]
