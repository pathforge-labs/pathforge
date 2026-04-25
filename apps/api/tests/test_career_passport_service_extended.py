"""
PathForge — Career Passport Service Extended Unit Tests
========================================================
Extended coverage targeting previously uncovered branches in
career_passport_service.py (visa/market/multi-country/full-scan/
dashboard aggregation/preferences/single-record retrieval paths).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.career_passport import (
    CareerPassportPreference,
    CountryComparison,
    CredentialMapping,
    MarketDemandEntry,
    VisaAssessment,
)
from app.models.user import User
from app.schemas.career_passport import CareerPassportPreferenceUpdate
from app.services.career_passport_service import (
    _get_salary_context,
    _get_years_experience,
    assess_visa,
    compare_countries,
    compare_multiple_countries,
    delete_credential_mapping,
    full_passport_scan,
    get_credential_mapping,
    get_dashboard,
    get_market_demand,
    get_market_demand_by_country,
    update_preferences,
)

# ── Paths for patching ────────────────────────────────────────────

ANALYZER_PATH = (
    "app.services.career_passport_service.CareerPassportAnalyzer"
)


# ── Helpers ───────────────────────────────────────────────────────


async def _make_user_and_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = False,
    primary_role: str | None = "Software Engineer",
    primary_industry: str | None = "Technology",
    seniority_level: str | None = "senior",
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Passport Ext",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role=primary_role,
        primary_industry=primary_industry,
        seniority_level=seniority_level,
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
            source="resume",
        )
        db.add(skill)
        await db.flush()

    return user, dna


def _fake_country_result() -> dict[str, object]:
    return {
        "col_delta_pct": 12.5,
        "salary_delta_pct": 20.0,
        "purchasing_power_delta": 7.5,
        "tax_impact_notes": "progressive",
        "market_demand_level": "high",
        "detailed_breakdown": {"rent": "high"},
    }


def _fake_visa_result() -> dict[str, object]:
    return {
        "visa_type": "highly_skilled",
        "eligibility_score": 0.72,
        "requirements": {"degree": "bachelor"},
        "processing_time_weeks": 6,
        "estimated_cost": "EUR 350",
        "notes": "Fast track",
    }


def _fake_market_result() -> dict[str, object]:
    return {
        "demand_level": "high",
        "open_positions_estimate": 1200,
        "yoy_growth_pct": 8.5,
        "top_employers": {"list": ["ING", "ASML"]},
        "salary_range_min": 55000.0,
        "salary_range_max": 95000.0,
        "currency": "EUR",
    }


def _fake_credential_result() -> dict[str, object]:
    return {
        "equivalent_level": "Master's degree",
        "eqf_level": "level_7",
        "recognition_notes": "Recognized",
        "framework_reference": "EQF",
        "confidence": 0.8,
    }


def _fake_score() -> dict[str, object]:
    return {
        "credential_score": 0.8,
        "visa_score": 0.7,
        "demand_score": 0.9,
        "financial_score": 0.6,
        "overall_score": 0.75,
    }


# ── _get_years_experience — blueprint branch (lines 66-68) ────────


class _Dummy:
    """Minimal stand-in for the ORM DNA object — bypasses SQLAlchemy descriptors."""

    def __init__(self, **attrs: object) -> None:
        self.__dict__.update(attrs)


class TestGetYearsExperienceBlueprint:
    def test_uses_blueprint_total_years(self) -> None:
        dna = _Dummy(experience_blueprint=SimpleNamespace(total_years=7.4))
        assert _get_years_experience(dna) == 7  # type: ignore[arg-type]

    def test_returns_at_least_1_when_blueprint_zero(self) -> None:
        dna = _Dummy(experience_blueprint=SimpleNamespace(total_years=0.0))
        assert _get_years_experience(dna) == 1  # type: ignore[arg-type]

    def test_falls_back_when_blueprint_missing_total_years(self) -> None:
        dna = _Dummy(experience_blueprint=SimpleNamespace(other_attr=5))
        # Attribute total_years missing → default 3
        assert _get_years_experience(dna) == 3  # type: ignore[arg-type]


# ── _get_salary_context — salary branch (line 75) ─────────────────


class TestGetSalaryContextWithSalary:
    def test_returns_formatted_salary_with_default_currency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.current_salary = 85000
        # salary_currency attribute absent → fallback EUR
        result = _get_salary_context(dna)
        assert "85000" in result
        assert "EUR" in result

    def test_returns_formatted_salary_with_custom_currency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.current_salary = 120000
        dna.salary_currency = "USD"
        result = _get_salary_context(dna)
        assert "120000" in result
        assert "USD" in result


# ── compare_countries (lines 179-209) ─────────────────────────────


class TestCompareCountries:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await compare_countries(
                db_session,
                user_id=uuid.uuid4(),
                source_country="Turkey",
                target_country="Netherlands",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_comparison(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="cc-happy@test.com",
        )
        with patch(
            f"{ANALYZER_PATH}.analyze_country_comparison",
            new=AsyncMock(return_value=_fake_country_result()),
        ):
            comparison = await compare_countries(
                db_session,
                user_id=user.id,
                source_country="Turkey",
                target_country="Netherlands",
            )

        assert comparison.id is not None
        assert comparison.source_country == "Turkey"
        assert comparison.target_country == "Netherlands"
        assert comparison.col_delta_pct == 12.5
        assert comparison.market_demand_level == "high"

    @pytest.mark.asyncio
    async def test_applies_defaults_when_dna_fields_none(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session,
            email="cc-defaults@test.com",
            primary_role=None,
            primary_industry=None,
            seniority_level=None,
        )
        spy = AsyncMock(return_value=_fake_country_result())
        with patch(f"{ANALYZER_PATH}.analyze_country_comparison", new=spy):
            await compare_countries(
                db_session,
                user_id=user.id,
                source_country="Germany",
                target_country="France",
            )
        kwargs = spy.call_args.kwargs
        assert kwargs["primary_role"] == "Software Engineer"
        assert kwargs["primary_industry"] == "Technology"
        assert kwargs["seniority_level"] == "mid"


# ── compare_multiple_countries (lines 236-266) ────────────────────


class TestCompareMultipleCountries:
    @pytest.mark.asyncio
    async def test_rejects_more_than_5_targets(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Maximum 5"):
            await compare_multiple_countries(
                db_session,
                user_id=uuid.uuid4(),
                source_country="Turkey",
                target_countries=["A", "B", "C", "D", "E", "F"],
            )

    @pytest.mark.asyncio
    async def test_returns_recommendation_and_scores(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="multi-ok@test.com",
        )
        # Build distinct scores so ordering is deterministic.
        # Spread comes first so that explicit overall_score overrides.
        scores_sequence = [
            {**_fake_score(), "overall_score": 0.4},
            {**_fake_score(), "overall_score": 0.9},
            {**_fake_score(), "overall_score": 0.6},
        ]
        with (
            patch(
                f"{ANALYZER_PATH}.analyze_country_comparison",
                new=AsyncMock(return_value=_fake_country_result()),
            ),
            patch(
                f"{ANALYZER_PATH}.compute_passport_score",
                MagicMock(side_effect=[dict(s) for s in scores_sequence]),
            ),
        ):
            output = await compare_multiple_countries(
                db_session,
                user_id=user.id,
                source_country="Turkey",
                target_countries=["NL", "DE", "FR"],
            )

        assert len(output["comparisons"]) == 3
        assert len(output["passport_scores"]) == 3
        # Highest score (0.9) → second target "DE"
        assert output["recommended_country"] == "DE"
        assert "scores highest" in output["recommendation_reasoning"]

    @pytest.mark.asyncio
    async def test_empty_targets_returns_none_recommendation(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="multi-empty@test.com",
        )
        result = await compare_multiple_countries(
            db_session,
            user_id=user.id,
            source_country="Turkey",
            target_countries=[],
        )
        assert result["comparisons"] == []
        assert result["passport_scores"] == []
        assert result["recommended_country"] is None
        assert result["recommendation_reasoning"] is None


# ── assess_visa (lines 302-332) ───────────────────────────────────


class TestAssessVisa:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await assess_visa(
                db_session,
                user_id=uuid.uuid4(),
                nationality="Turkish",
                target_country="Netherlands",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_assessment(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="visa-ok@test.com",
        )
        with patch(
            f"{ANALYZER_PATH}.analyze_visa_feasibility",
            new=AsyncMock(return_value=_fake_visa_result()),
        ):
            assessment = await assess_visa(
                db_session,
                user_id=user.id,
                nationality="Turkish",
                target_country="Netherlands",
            )
        assert assessment.id is not None
        assert assessment.visa_type == "highly_skilled"
        assert assessment.eligibility_score == 0.72
        assert assessment.processing_time_weeks == 6

    @pytest.mark.asyncio
    async def test_uses_analyzer_result_defaults_when_fields_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="visa-def@test.com",
        )
        with patch(
            f"{ANALYZER_PATH}.analyze_visa_feasibility",
            new=AsyncMock(return_value={}),
        ):
            assessment = await assess_visa(
                db_session,
                user_id=user.id,
                nationality="Turkish",
                target_country="Netherlands",
            )
        assert assessment.visa_type == "other"
        assert assessment.eligibility_score == 0.0


# ── get_market_demand (lines 361-395) ─────────────────────────────


class TestGetMarketDemand:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await get_market_demand(
                db_session,
                user_id=uuid.uuid4(),
                country="Netherlands",
            )

    @pytest.mark.asyncio
    async def test_uses_dna_defaults_when_role_and_industry_absent(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="md-defaults@test.com", with_skills=True,
        )
        spy = AsyncMock(return_value=_fake_market_result())
        with patch(f"{ANALYZER_PATH}.analyze_market_demand", new=spy):
            entry = await get_market_demand(
                db_session,
                user_id=user.id,
                country="Netherlands",
            )
        kwargs = spy.call_args.kwargs
        assert kwargs["role"] == "Software Engineer"
        assert kwargs["industry"] == "Technology"
        assert entry.country == "Netherlands"
        assert entry.demand_level == "high"
        assert entry.open_positions_estimate == 1200

    @pytest.mark.asyncio
    async def test_explicit_role_and_industry_override_dna(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="md-override@test.com",
        )
        spy = AsyncMock(return_value=_fake_market_result())
        with patch(f"{ANALYZER_PATH}.analyze_market_demand", new=spy):
            entry = await get_market_demand(
                db_session,
                user_id=user.id,
                country="Germany",
                role="Data Scientist",
                industry="Finance",
            )
        kwargs = spy.call_args.kwargs
        assert kwargs["role"] == "Data Scientist"
        assert kwargs["industry"] == "Finance"
        assert entry.role == "Data Scientist"
        assert entry.industry == "Finance"

    @pytest.mark.asyncio
    async def test_fallback_when_dna_role_missing_and_no_param(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session,
            email="md-fallback@test.com",
            primary_role=None,
            primary_industry=None,
            seniority_level=None,
        )
        spy = AsyncMock(return_value=_fake_market_result())
        with patch(f"{ANALYZER_PATH}.analyze_market_demand", new=spy):
            entry = await get_market_demand(
                db_session,
                user_id=user.id,
                country="Spain",
            )
        assert entry.role == "Software Engineer"
        assert entry.industry == "Technology"


# ── full_passport_scan (lines 433-469) ────────────────────────────


class TestFullPassportScan:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await full_passport_scan(
                db_session,
                user_id=uuid.uuid4(),
                source_qualification="BSc CS",
                source_country="Turkey",
                target_country="Netherlands",
                nationality="Turkish",
            )

    @pytest.mark.asyncio
    async def test_returns_all_components(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="scan-ok@test.com", with_skills=True,
        )
        with (
            patch(
                f"{ANALYZER_PATH}.analyze_credential_mapping",
                new=AsyncMock(return_value=_fake_credential_result()),
            ),
            patch(
                f"{ANALYZER_PATH}.compute_credential_confidence",
                MagicMock(return_value=0.80),
            ),
            patch(
                f"{ANALYZER_PATH}.analyze_country_comparison",
                new=AsyncMock(return_value=_fake_country_result()),
            ),
            patch(
                f"{ANALYZER_PATH}.analyze_visa_feasibility",
                new=AsyncMock(return_value=_fake_visa_result()),
            ),
            patch(
                f"{ANALYZER_PATH}.analyze_market_demand",
                new=AsyncMock(return_value=_fake_market_result()),
            ),
            patch(
                f"{ANALYZER_PATH}.compute_passport_score",
                MagicMock(return_value={**_fake_score(), "overall_score": 0.78}),
            ),
        ):
            result = await full_passport_scan(
                db_session,
                user_id=user.id,
                source_qualification="BSc CS",
                source_country="Turkey",
                target_country="Netherlands",
                nationality="Turkish",
            )

        assert isinstance(result["credential_mapping"], CredentialMapping)
        assert isinstance(result["country_comparison"], CountryComparison)
        assert isinstance(result["visa_assessment"], VisaAssessment)
        assert isinstance(result["market_demand"], MarketDemandEntry)
        assert result["passport_score"]["target_country"] == "Netherlands"
        assert result["passport_score"]["overall_score"] == 0.78


# ── get_dashboard aggregation (lines 548-569) ─────────────────────


class TestGetDashboardAggregation:
    @pytest.mark.asyncio
    async def test_aggregates_passport_scores_per_unique_target(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dash-agg@test.com",
        )
        # Seed two comparisons for same target + one different target
        for target in ("Netherlands", "Netherlands", "Germany"):
            db_session.add(CountryComparison(
                career_dna_id=dna.id,
                user_id=user.id,
                source_country="Turkey",
                target_country=target,
                col_delta_pct=1.0,
                salary_delta_pct=2.0,
                purchasing_power_delta=3.0,
                market_demand_level="high",
            ))
        # Seed matching credential + visa so the lookup loops execute
        db_session.add(CredentialMapping(
            career_dna_id=dna.id,
            user_id=user.id,
            source_qualification="BSc CS",
            source_country="Turkey",
            target_country="Netherlands",
            equivalent_level="Master's",
            eqf_level="level_7",
            confidence_score=0.77,
        ))
        db_session.add(VisaAssessment(
            career_dna_id=dna.id,
            user_id=user.id,
            nationality="Turkish",
            target_country="Netherlands",
            visa_type="highly_skilled",
            eligibility_score=0.7,
        ))
        await db_session.flush()

        # Use side_effect so each invocation gets a fresh dict —
        # otherwise `score["target_country"] = ...` would alias across
        # iterations and clobber prior entries.
        with patch(
            f"{ANALYZER_PATH}.compute_passport_score",
            MagicMock(side_effect=lambda **_kwargs: {**_fake_score()}),
        ) as spy:
            result = await get_dashboard(db_session, user_id=user.id)

        # De-duplication: 2 unique targets
        assert len(result["passport_scores"]) == 2
        targets = {s["target_country"] for s in result["passport_scores"]}
        assert targets == {"Netherlands", "Germany"}
        # compute_passport_score invoked exactly twice (unique targets only)
        assert spy.call_count == 2

    @pytest.mark.asyncio
    async def test_dashboard_returns_preferences_when_present(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dash-pref@test.com",
        )
        db_session.add(CareerPassportPreference(
            career_dna_id=dna.id,
            user_id=user.id,
            nationality="Turkish",
        ))
        await db_session.flush()

        result = await get_dashboard(db_session, user_id=user.id)
        assert result["preferences"] is not None
        assert result["preferences"].nationality == "Turkish"


# ── update_preferences — all individual field branches (638-646) ──


class TestUpdatePreferencesFieldBranches:
    @pytest.mark.asyncio
    async def test_sets_preferred_countries(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pref-countries@test.com",
        )
        update = CareerPassportPreferenceUpdate(
            preferred_countries=["NL", "DE"],
        )
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.preferred_countries == {"countries": ["NL", "DE"]}

    @pytest.mark.asyncio
    async def test_sets_include_visa_info_false(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pref-visa@test.com",
        )
        update = CareerPassportPreferenceUpdate(include_visa_info=False)
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.include_visa_info is False

    @pytest.mark.asyncio
    async def test_sets_include_col_comparison_false(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pref-col@test.com",
        )
        update = CareerPassportPreferenceUpdate(include_col_comparison=False)
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.include_col_comparison is False

    @pytest.mark.asyncio
    async def test_sets_include_market_demand_false(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pref-md@test.com",
        )
        update = CareerPassportPreferenceUpdate(include_market_demand=False)
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.include_market_demand is False

    @pytest.mark.asyncio
    async def test_updates_existing_record_with_all_fields(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pref-all@test.com",
        )
        # First create
        await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerPassportPreferenceUpdate(nationality="Turkish"),
        )
        # Then update all fields (hits every truthy-branch)
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=CareerPassportPreferenceUpdate(
                preferred_countries=["NL"],
                nationality="Dutch",
                include_visa_info=True,
                include_col_comparison=False,
                include_market_demand=True,
            ),
        )
        assert pref.nationality == "Dutch"
        assert pref.preferred_countries == {"countries": ["NL"]}
        assert pref.include_col_comparison is False


# ── get_credential_mapping & delete_credential_mapping ────────────


class TestSingleCredentialRetrieval:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_credential_mapping(
            db_session,
            mapping_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_mapping_when_exists(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="get-cm@test.com",
        )
        mapping = CredentialMapping(
            career_dna_id=dna.id,
            user_id=user.id,
            source_qualification="BSc CS",
            source_country="Turkey",
            target_country="Netherlands",
            equivalent_level="Master's",
            eqf_level="level_7",
            confidence_score=0.75,
        )
        db_session.add(mapping)
        await db_session.flush()

        fetched = await get_credential_mapping(
            db_session, mapping_id=mapping.id, user_id=user.id,
        )
        assert fetched is not None
        assert fetched.id == mapping.id

    @pytest.mark.asyncio
    async def test_get_respects_user_scope(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="scope-cm@test.com",
        )
        mapping = CredentialMapping(
            career_dna_id=dna.id,
            user_id=user.id,
            source_qualification="BSc CS",
            source_country="Turkey",
            target_country="Netherlands",
            equivalent_level="Master's",
            eqf_level="level_7",
            confidence_score=0.75,
        )
        db_session.add(mapping)
        await db_session.flush()

        # Different user_id must not retrieve
        fetched = await get_credential_mapping(
            db_session, mapping_id=mapping.id, user_id=uuid.uuid4(),
        )
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        deleted = await delete_credential_mapping(
            db_session,
            mapping_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_removed(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="del-cm@test.com",
        )
        mapping = CredentialMapping(
            career_dna_id=dna.id,
            user_id=user.id,
            source_qualification="BSc CS",
            source_country="Turkey",
            target_country="Netherlands",
            equivalent_level="Master's",
            eqf_level="level_7",
            confidence_score=0.75,
        )
        db_session.add(mapping)
        await db_session.flush()
        mapping_id = mapping.id

        deleted = await delete_credential_mapping(
            db_session, mapping_id=mapping_id, user_id=user.id,
        )
        assert deleted is True

        follow_up = await get_credential_mapping(
            db_session, mapping_id=mapping_id, user_id=user.id,
        )
        assert follow_up is None


# ── get_market_demand_by_country (lines 707-715) ──────────────────


class TestGetMarketDemandByCountry:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_entries(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_market_demand_by_country(
            db_session, country="Netherlands", user_id=uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_only_matching_country_and_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="md-by-country@test.com",
        )
        # Seed 3 entries: 2 matching country, 1 different country
        for country in ("Netherlands", "Netherlands", "Germany"):
            db_session.add(MarketDemandEntry(
                career_dna_id=dna.id,
                user_id=user.id,
                country=country,
                role="Software Engineer",
                industry="Technology",
                demand_level="high",
            ))
        await db_session.flush()

        results = await get_market_demand_by_country(
            db_session, country="Netherlands", user_id=user.id,
        )
        assert len(results) == 2
        assert all(entry.country == "Netherlands" for entry in results)
