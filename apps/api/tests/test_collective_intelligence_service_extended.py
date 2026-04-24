"""
PathForge — Collective Intelligence Service Extended Unit Tests
=================================================================
Targets missing coverage: lines 78-80 (helper edge), 257-303 (peer cohort),
330-365 (career pulse), 475-501 (run_intelligence_scan),
533-580 (compare_industries), and 645 (prefs list conversion).

LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, ExperienceBlueprint, SkillGenomeEntry
from app.models.user import User
from app.services.collective_intelligence_service import (
    _get_years_experience,
    compare_industries,
    get_career_pulse,
    get_or_update_preferences,
    get_peer_cohort_analysis,
    run_intelligence_scan,
)

# ── Test Helpers ──────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 2,
    with_blueprint: bool = False,
    total_years: float = 5.0,
    primary_role: str | None = "Data Engineer",
    primary_industry: str | None = "Technology",
    seniority_level: str | None = "senior",
    location: str | None = "Amsterdam",
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
        primary_role=primary_role,
        primary_industry=primary_industry,
        seniority_level=seniority_level,
        location=location,
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

    if with_blueprint:
        blueprint = ExperienceBlueprint(
            career_dna_id=dna.id,
            total_years=total_years,
            role_count=3,
            avg_tenure_months=18.0,
            industry_diversity=0.5,
        )
        db.add(blueprint)
        await db.flush()
        await db.refresh(dna)

    return user, dna


def _pulse_result() -> dict[str, Any]:
    return {
        "pulse_score": 72.5,
        "pulse_category": "strong",
        "trend_direction": "rising",
        "demand_component": 80.0,
        "salary_component": 70.0,
        "skill_relevance_component": 75.0,
        "trend_component": 65.0,
        "top_opportunities": ["A", "B"],
        "risk_factors": ["X"],
        "recommended_actions": ["do Y"],
        "summary": "strong pulse",
        "confidence": 0.82,
    }


def _snapshot_result(
    *,
    trend: str = "rising",
    demand: str = "high",
    confidence: float = 0.8,
) -> dict[str, Any]:
    return {
        "trend_direction": trend,
        "demand_intensity": demand,
        "top_emerging_skills": ["AI"],
        "declining_skills": ["Legacy"],
        "avg_salary_range_min": 50000.0,
        "avg_salary_range_max": 90000.0,
        "growth_rate_pct": 8.0,
        "hiring_volume_trend": "up",
        "key_insights": "Demand rising",
        "confidence": confidence,
    }


def _benchmark_result() -> dict[str, Any]:
    return {
        "benchmark_min": 60000.0,
        "benchmark_median": 80000.0,
        "benchmark_max": 100000.0,
        "user_percentile": 70.0,
        "skill_premium_pct": 10.0,
        "experience_factor": 1.2,
        "negotiation_insights": "strong leverage",
        "premium_skills": ["Python"],
        "confidence": 0.8,
    }


def _cohort_result() -> dict[str, Any]:
    return {
        "cohort_size": 50,
        "user_rank_percentile": 75.0,
        "avg_skills_count": 10.0,
        "avg_experience_years": 6.0,
        "common_transitions": ["Eng -> Lead"],
        "top_differentiating_skills": ["K8s"],
        "skill_gaps_vs_cohort": ["MLOps"],
        "confidence": 0.85,
    }


# ── _get_years_experience: lines 78-80 ────────────────────────────


class TestGetYearsExperienceWithBlueprint:
    """Lines 78-80: blueprint present + has total_years -> max(1, int(total_years))."""

    def test_returns_total_years_when_blueprint_set(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        bp = ExperienceBlueprint(career_dna_id=uuid.uuid4(), total_years=7.2)
        dna.experience_blueprint = bp
        assert _get_years_experience(dna) == 7

    def test_returns_at_least_one_when_zero_years(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        bp = ExperienceBlueprint(career_dna_id=uuid.uuid4(), total_years=0.0)
        dna.experience_blueprint = bp
        assert _get_years_experience(dna) == 1

    def test_handles_fractional_years_floor(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        bp = ExperienceBlueprint(career_dna_id=uuid.uuid4(), total_years=4.9)
        dna.experience_blueprint = bp
        assert _get_years_experience(dna) == 4


# ── get_peer_cohort_analysis: lines 257-303 ──────────────────────


class TestGetPeerCohortAnalysis:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_peer_cohort_analysis(
                db_session, user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_cohort(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-coh1@test.com")

        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
            new=AsyncMock(return_value=_cohort_result()),
        ):
            cohort = await get_peer_cohort_analysis(
                db_session,
                user_id=user.id,
                role="Data Engineer",
                experience_range_min=3,
                experience_range_max=7,
                region="Netherlands",
            )

        assert cohort.id is not None
        assert cohort.cohort_size == 50
        assert cohort.user_rank_percentile == 75.0
        assert cohort.confidence_score == 0.85
        assert cohort.cohort_criteria["role"] == "Data Engineer"
        assert cohort.cohort_criteria["experience_range"] == "3-7"
        assert cohort.cohort_criteria["region"] == "Netherlands"

    @pytest.mark.asyncio
    async def test_defaults_experience_range_from_dna(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-coh2@test.com")

        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
            new=AsyncMock(return_value=_cohort_result()),
        ):
            cohort = await get_peer_cohort_analysis(
                db_session, user_id=user.id,
            )

        # Default years_exp is 3, so min = max(0, 3-2)=1, max = 3+2=5
        assert cohort.cohort_criteria["experience_range"] == "1-5"

    @pytest.mark.asyncio
    async def test_uses_defaults_when_dna_fields_none(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session,
            email="ci-coh3@test.com",
            primary_role=None,
            primary_industry=None,
            location=None,
        )
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
            new=AsyncMock(return_value=_cohort_result()),
        ):
            cohort = await get_peer_cohort_analysis(
                db_session, user_id=user.id,
            )
        assert cohort.cohort_criteria["role"] == "Software Engineer"
        assert cohort.cohort_criteria["region"] == "Global"
        assert cohort.cohort_criteria["industry"] == "Technology"

    @pytest.mark.asyncio
    async def test_empty_analyzer_result_uses_defaults(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-coh4@test.com")
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
            new=AsyncMock(return_value={}),
        ):
            cohort = await get_peer_cohort_analysis(
                db_session, user_id=user.id,
            )
        assert cohort.cohort_size == 10
        assert cohort.user_rank_percentile == 50.0
        assert cohort.avg_skills_count == 0.0
        assert cohort.avg_experience_years == 0.0
        assert cohort.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_clamps_min_to_zero_for_low_experience(
        self, db_session: AsyncSession,
    ) -> None:
        # Default years_exp=3 -> min = max(0, 1) = 1; force blueprint=0y
        user, _dna = await _make_dna(
            db_session,
            email="ci-coh5@test.com",
            with_blueprint=True,
            total_years=0.0,
        )
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
            new=AsyncMock(return_value=_cohort_result()),
        ):
            cohort = await get_peer_cohort_analysis(
                db_session, user_id=user.id,
            )
        # total_years=0 -> max(1, 0) -> years_exp=1, min=max(0,1-2)=0, max=3
        assert cohort.cohort_criteria["experience_range"] == "0-3"


# ── get_career_pulse: lines 330-365 ──────────────────────────────


class TestGetCareerPulse:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_career_pulse(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_happy_path_persists_pulse(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pulse1@test.com")

        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
            new=AsyncMock(return_value=_pulse_result()),
        ):
            pulse = await get_career_pulse(
                db_session,
                user_id=user.id,
                industry="Technology",
                region="Netherlands",
            )

        assert pulse.id is not None
        assert pulse.pulse_score == 72.5
        assert pulse.pulse_category == "strong"
        assert pulse.trend_direction == "rising"
        assert pulse.confidence_score == 0.82

    @pytest.mark.asyncio
    async def test_uses_defaults_when_analyzer_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pulse2@test.com")
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
            new=AsyncMock(return_value={}),
        ):
            pulse = await get_career_pulse(db_session, user_id=user.id)
        assert pulse.pulse_score == 50.0
        assert pulse.pulse_category == "moderate"
        assert pulse.trend_direction == "stable"
        assert pulse.demand_component == 50.0
        assert pulse.salary_component == 50.0
        assert pulse.skill_relevance_component == 50.0
        assert pulse.trend_component == 50.0
        assert pulse.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_falls_back_to_dna_industry_and_region(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pulse3@test.com")
        mock = AsyncMock(return_value=_pulse_result())
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
            new=mock,
        ):
            await get_career_pulse(db_session, user_id=user.id)
        kwargs = mock.call_args.kwargs
        assert kwargs["industry"] == "Technology"
        assert kwargs["region"] == "Amsterdam"

    @pytest.mark.asyncio
    async def test_uses_global_defaults_when_dna_missing_fields(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session,
            email="ci-pulse4@test.com",
            primary_industry=None,
            location=None,
            primary_role=None,
            seniority_level=None,
        )
        mock = AsyncMock(return_value=_pulse_result())
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
            new=mock,
        ):
            await get_career_pulse(db_session, user_id=user.id)
        kwargs = mock.call_args.kwargs
        assert kwargs["industry"] == "Technology"
        assert kwargs["region"] == "Global"
        assert kwargs["primary_role"] == "Software Engineer"
        assert kwargs["seniority_level"] == "mid"


# ── run_intelligence_scan: lines 475-501 ─────────────────────────


class TestRunIntelligenceScan:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await run_intelligence_scan(db_session, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_full_scan_returns_all_components(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-scan1@test.com")
        with (
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
                new=AsyncMock(return_value=_pulse_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
                new=AsyncMock(return_value=_snapshot_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_salary_benchmark",
                new=AsyncMock(return_value=_benchmark_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
                new=AsyncMock(return_value=_cohort_result()),
            ),
        ):
            result = await run_intelligence_scan(
                db_session,
                user_id=user.id,
                industry="Finance",
                region="Germany",
                currency="USD",
            )

        assert result["career_pulse"].pulse_score == 72.5
        assert result["industry_snapshot"].industry == "Finance"
        assert result["industry_snapshot"].region == "Germany"
        assert result["salary_benchmark"].currency == "USD"
        assert result["peer_cohort"].cohort_size == 50

    @pytest.mark.asyncio
    async def test_scan_defaults_to_dna_industry_and_region(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-scan2@test.com")
        with (
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
                new=AsyncMock(return_value=_pulse_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
                new=AsyncMock(return_value=_snapshot_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_salary_benchmark",
                new=AsyncMock(return_value=_benchmark_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
                new=AsyncMock(return_value=_cohort_result()),
            ),
        ):
            result = await run_intelligence_scan(
                db_session, user_id=user.id,
            )
        assert result["industry_snapshot"].industry == "Technology"
        assert result["industry_snapshot"].region == "Amsterdam"

    @pytest.mark.asyncio
    async def test_scan_uses_global_when_dna_fields_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session,
            email="ci-scan3@test.com",
            primary_industry=None,
            location=None,
        )
        with (
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_career_pulse",
                new=AsyncMock(return_value=_pulse_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
                new=AsyncMock(return_value=_snapshot_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_salary_benchmark",
                new=AsyncMock(return_value=_benchmark_result()),
            ),
            patch(
                "app.services.collective_intelligence_service"
                ".CollectiveIntelligenceAnalyzer.analyze_peer_cohort",
                new=AsyncMock(return_value=_cohort_result()),
            ),
        ):
            result = await run_intelligence_scan(
                db_session, user_id=user.id,
            )
        assert result["industry_snapshot"].industry == "Technology"
        assert result["industry_snapshot"].region == "Global"


# ── compare_industries: lines 533-580 ────────────────────────────


class TestCompareIndustries:
    @pytest.mark.asyncio
    async def test_raises_when_too_many_industries(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Maximum 5"):
            await compare_industries(
                db_session,
                user_id=uuid.uuid4(),
                industries=["A", "B", "C", "D", "E", "F"],
                region="EU",
            )

    @pytest.mark.asyncio
    async def test_raises_when_too_few_industries(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="At least 2"):
            await compare_industries(
                db_session,
                user_id=uuid.uuid4(),
                industries=["Solo"],
                region="EU",
            )

    @pytest.mark.asyncio
    async def test_empty_list_raises(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="At least 2"):
            await compare_industries(
                db_session,
                user_id=uuid.uuid4(),
                industries=[],
                region="EU",
            )

    @pytest.mark.asyncio
    async def test_recommends_highest_composite_score(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-cmp1@test.com")

        # Provide distinct results per industry via side_effect
        results = [
            _snapshot_result(trend="stable", demand="low"),       # low composite
            _snapshot_result(trend="emerging", demand="critical"),  # highest
            _snapshot_result(trend="rising", demand="high"),      # mid-high
        ]
        mock = AsyncMock(side_effect=results)
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=mock,
        ):
            out = await compare_industries(
                db_session,
                user_id=user.id,
                industries=["Retail", "AI", "Finance"],
                region="EU",
            )

        assert len(out["snapshots"]) == 3
        assert out["recommended_industry"] == "AI"
        assert "AI" in out["recommendation_reasoning"]
        assert "critical" in out["recommendation_reasoning"]
        assert "emerging" in out["recommendation_reasoning"]

    @pytest.mark.asyncio
    async def test_two_industries_minimum_allowed(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-cmp2@test.com")
        mock = AsyncMock(return_value=_snapshot_result())
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=mock,
        ):
            out = await compare_industries(
                db_session,
                user_id=user.id,
                industries=["X", "Y"],
                region="EU",
            )
        assert len(out["snapshots"]) == 2
        assert out["recommended_industry"] in {"X", "Y"}

    @pytest.mark.asyncio
    async def test_five_industries_exact_boundary(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-cmp3@test.com")
        mock = AsyncMock(return_value=_snapshot_result())
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=mock,
        ):
            out = await compare_industries(
                db_session,
                user_id=user.id,
                industries=["A", "B", "C", "D", "E"],
                region="EU",
            )
        assert len(out["snapshots"]) == 5

    @pytest.mark.asyncio
    async def test_unknown_demand_and_trend_use_default_scores(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-cmp4@test.com")
        unknown = _snapshot_result(trend="mystery", demand="unknown")
        rising = _snapshot_result(trend="rising", demand="high")
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=AsyncMock(side_effect=[unknown, rising]),
        ):
            out = await compare_industries(
                db_session,
                user_id=user.id,
                industries=["Alpha", "Beta"],
                region="EU",
            )
        # rising/high should beat unknown (which defaults to 0.5/0.5)
        assert out["recommended_industry"] == "Beta"

    @pytest.mark.asyncio
    async def test_reasoning_contains_profile_phrase(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-cmp5@test.com")
        with patch(
            "app.services.collective_intelligence_service"
            ".CollectiveIntelligenceAnalyzer.analyze_industry_snapshot",
            new=AsyncMock(return_value=_snapshot_result()),
        ):
            out = await compare_industries(
                db_session,
                user_id=user.id,
                industries=["X", "Y"],
                region="EU",
            )
        assert "Career DNA profile" in out["recommendation_reasoning"]


# ── get_or_update_preferences: line 645 (list -> dict wrap) ──────


class TestPreferencesListConversion:
    @pytest.mark.asyncio
    async def test_preferred_industries_list_converted_to_dict(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pref-ind@test.com")
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"preferred_industries": ["Tech", "Finance"]},
        )
        assert pref.preferred_industries == {"items": ["Tech", "Finance"]}

    @pytest.mark.asyncio
    async def test_preferred_locations_list_converted_to_dict(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pref-loc@test.com")
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"preferred_locations": ["NL", "DE"]},
        )
        assert pref.preferred_locations == {"items": ["NL", "DE"]}

    @pytest.mark.asyncio
    async def test_disallowed_field_is_ignored(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pref-bad@test.com")
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"malicious_field": "oops", "preferred_currency": "GBP"},
        )
        assert pref.preferred_currency == "GBP"
        assert not hasattr(pref, "malicious_field") or getattr(
            pref, "malicious_field", None,
        ) != "oops"

    @pytest.mark.asyncio
    async def test_none_value_is_skipped(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ci-pref-none@test.com")
        # First set a real value
        await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"preferred_currency": "EUR"},
        )
        # Then pass None — should not overwrite
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"preferred_currency": None},
        )
        assert pref.preferred_currency == "EUR"

    @pytest.mark.asyncio
    async def test_preferred_industries_dict_passes_through(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session, email="ci-pref-dict@test.com",
        )
        # Non-list value must be stored as-is (not wrapped)
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={"preferred_industries": {"items": ["Health"]}},
        )
        assert pref.preferred_industries == {"items": ["Health"]}

    @pytest.mark.asyncio
    async def test_boolean_allowed_field_updates(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session, email="ci-pref-bool@test.com",
        )
        pref = await get_or_update_preferences(
            db_session,
            user_id=user.id,
            updates={
                "include_industry_pulse": False,
                "include_salary_benchmarks": False,
                "include_peer_analysis": True,
            },
        )
        assert pref.include_industry_pulse is False
        assert pref.include_salary_benchmarks is False
        assert pref.include_peer_analysis is True
