"""
PathForge - Hidden Job Market Service Unit Tests
==================================================
Service-layer tests for hidden_job_market_service.py.

LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
Covers pure helpers, happy paths, defaults, and error handling.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, ExperienceBlueprint, SkillGenomeEntry
from app.models.hidden_job_market import (
    CompanySignal,
    HiddenJobMarketPreference,
    HiddenOpportunity,
    OutreachTemplate,
    SignalMatchResult,
    SignalStatus,
)
from app.models.user import User
from app.schemas.hidden_job_market import (
    DismissSignalRequest,
    GenerateOutreachRequest,
    HiddenJobMarketPreferenceUpdateRequest,
)
from app.services.hidden_job_market_service import (
    _default_signal_analysis,
    _format_skills_for_prompt,
    _get_career_dna_with_context,
    _get_years_experience,
    _load_signal_with_relations,
    _store_match_result,
    _store_opportunities,
    _store_outreach,
    compare_signals,
    dismiss_signal,
    generate_outreach,
    get_dashboard,
    get_opportunity_radar,
    get_preferences,
    get_signal,
    scan_company,
    surface_opportunities,
    update_preferences,
)

# ── Helpers ──────────────────────────────────────────────────────


async def _make_user_and_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 2,
    with_blueprint: bool = False,
    blueprint_years: float = 5.0,
    primary_role: str | None = "Software Engineer",
    primary_industry: str | None = "Technology",
    seniority_level: str | None = "senior",
    completeness_score: float = 0.8,
) -> tuple[User, CareerDNA]:
    """Create a user with a CareerDNA record for tests."""
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="HJM Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role=primary_role,
        primary_industry=primary_industry,
        seniority_level=seniority_level,
        location="Amsterdam",
        completeness_score=completeness_score,
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
                confidence=0.85,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    if with_blueprint:
        blueprint = ExperienceBlueprint(
            career_dna_id=dna.id,
            total_years=blueprint_years,
            role_count=3,
            avg_tenure_months=18.0,
            career_direction="exploring",
            industry_diversity=0.3,
        )
        db.add(blueprint)
        await db.flush()

    return user, dna


async def _make_signal(
    db: AsyncSession,
    *,
    user: User,
    dna: CareerDNA,
    company_name: str = "Acme Corp",
    signal_type: str = "funding",
    title: str = "Series B funding round",
    strength: float = 0.7,
    status: str = "detected",
) -> CompanySignal:
    """Create a persisted CompanySignal."""
    signal = CompanySignal(
        career_dna_id=dna.id,
        user_id=user.id,
        company_name=company_name,
        signal_type=signal_type,
        title=title,
        description="A growth signal.",
        strength=strength,
        source="TechCrunch",
        status=status,
        confidence_score=0.5,
    )
    db.add(signal)
    await db.flush()
    return signal


# ── Pure helper tests (no mocking needed) ────────────────────────


class TestFormatSkillsForPrompt:
    def test_returns_fallback_when_no_skills(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_formats_single_skill(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Python",
            proficiency_level="expert",
        )
        dna.skill_genome = [skill]
        assert _format_skills_for_prompt(dna) == "Python (expert)"

    def test_formats_multiple_skills_joined_by_comma(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Python",
                proficiency_level="expert",
            ),
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Rust",
                proficiency_level="intermediate",
            ),
        ]
        result = _format_skills_for_prompt(dna)
        assert "Python (expert)" in result
        assert "Rust (intermediate)" in result
        assert ", " in result


class TestGetYearsExperience:
    def test_returns_default_when_no_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        assert _get_years_experience(dna) == 3

    def test_returns_total_years_when_blueprint_set(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = MagicMock()
        blueprint.total_years = 8.5
        dna.experience_blueprint = blueprint
        assert _get_years_experience(dna) == 8

    def test_returns_minimum_one_year(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = MagicMock()
        blueprint.total_years = 0.0
        dna.experience_blueprint = blueprint
        assert _get_years_experience(dna) == 1


class TestStoreMatchResult:
    def test_populates_all_fields(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        data = {
            "match_score": 0.82,
            "skill_overlap": 0.75,
            "role_relevance": 0.9,
            "explanation": "Strong match",
            "matched_skills": {"python": 0.9},
            "relevance_reasoning": "Role fits",
        }
        record = _store_match_result(signal, data)
        assert record.signal_id == signal.id
        assert record.match_score == 0.82
        assert record.skill_overlap == 0.75
        assert record.role_relevance == 0.9
        assert record.explanation == "Strong match"
        assert record.matched_skills == {"python": 0.9}

    def test_uses_defaults_when_fields_missing(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        record = _store_match_result(signal, {})
        assert record.match_score == 0.0
        assert record.skill_overlap == 0.0
        assert record.role_relevance == 0.0
        assert record.explanation is None


class TestStoreOutreach:
    def test_populates_all_fields(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        data = {
            "subject_line": "Hello!",
            "body": "Body content",
            "personalization_points": {"x": 1},
            "confidence": 0.77,
        }
        record = _store_outreach(signal, data, "introduction", "casual")
        assert record.signal_id == signal.id
        assert record.subject_line == "Hello!"
        assert record.body == "Body content"
        assert record.template_type == "introduction"
        assert record.tone == "casual"
        assert record.confidence == 0.77

    def test_uses_default_subject_line_when_missing(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        record = _store_outreach(signal, {}, "introduction", "professional")
        assert record.subject_line == "Connection opportunity"
        assert record.body == ""
        assert record.confidence == 0.5


class TestStoreOpportunities:
    def test_returns_empty_list_on_empty_input(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        assert _store_opportunities(signal, []) == []

    def test_creates_record_per_input(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        data = [
            {
                "predicted_role": "Staff Engineer",
                "predicted_seniority": "staff",
                "predicted_timeline_days": 45,
                "probability": 0.8,
                "reasoning": "Growth team",
                "required_skills": {"python": 0.9},
                "salary_range_min": 90000,
                "salary_range_max": 140000,
                "currency": "USD",
            },
            {
                "predicted_role": "Senior Engineer",
                "probability": 0.6,
            },
        ]
        records = _store_opportunities(signal, data)
        assert len(records) == 2
        assert records[0].predicted_role == "Staff Engineer"
        assert records[0].currency == "USD"
        assert records[1].predicted_role == "Senior Engineer"

    def test_uses_defaults_when_fields_missing(self) -> None:
        signal = MagicMock()
        signal.id = uuid.uuid4()
        records = _store_opportunities(signal, [{}])
        assert len(records) == 1
        assert records[0].predicted_role == "Unknown role"
        assert records[0].probability == 0.0
        assert records[0].currency == "EUR"


class TestDefaultSignalAnalysis:
    def test_returns_safe_fallback_structure(self) -> None:
        result = _default_signal_analysis("TestCo")
        assert result["signals"] == []
        assert "TestCo" in result["company_summary"]


# ── _get_career_dna_with_context ────────────────────────────────


class TestGetCareerDnaWithContext:
    async def test_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        result = await _get_career_dna_with_context(db_session, uuid.uuid4())
        assert result is None

    async def test_returns_dna_when_exists(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="getdna@test.com")
        result = await _get_career_dna_with_context(db_session, user.id)
        assert result is not None
        assert result.id == dna.id


# ── get_dashboard ───────────────────────────────────────────────


class TestGetDashboard:
    async def test_returns_empty_structure_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["signals"] == []
        assert result["preferences"] is None
        assert result["total_signals"] == 0
        assert result["active_signals"] == 0
        assert result["matched_signals"] == 0
        assert result["dismissed_signals"] == 0
        assert result["total_opportunities"] == 0

    async def test_returns_empty_lists_with_dna_but_no_signals(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="dash-empty@test.com",
        )
        result = await get_dashboard(db_session, user_id=user.id)
        assert result["total_signals"] == 0
        assert result["active_signals"] == 0
        assert result["preferences"] is None

    async def test_counts_signals_by_status(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dash-counts@test.com",
        )
        await _make_signal(
            db_session, user=user, dna=dna, status=SignalStatus.DETECTED.value,
        )
        await _make_signal(
            db_session, user=user, dna=dna, status=SignalStatus.MATCHED.value,
        )
        await _make_signal(
            db_session, user=user, dna=dna, status=SignalStatus.DISMISSED.value,
        )
        await db_session.commit()

        result = await get_dashboard(db_session, user_id=user.id)
        assert result["total_signals"] == 3
        assert result["active_signals"] == 2  # detected + matched
        assert result["matched_signals"] == 1
        assert result["dismissed_signals"] == 1

    async def test_includes_preferences_when_set(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dash-pref@test.com",
        )
        pref = HiddenJobMarketPreference(
            career_dna_id=dna.id,
            user_id=user.id,
            min_signal_strength=0.4,
        )
        db_session.add(pref)
        await db_session.commit()

        result = await get_dashboard(db_session, user_id=user.id)
        assert result["preferences"] is not None
        assert result["preferences"].min_signal_strength == 0.4

    async def test_counts_opportunities_across_signals(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dash-opps@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        opp = HiddenOpportunity(
            signal_id=signal.id,
            predicted_role="Senior Eng",
            probability=0.8,
        )
        db_session.add(opp)
        await db_session.commit()

        result = await get_dashboard(db_session, user_id=user.id)
        assert result["total_opportunities"] == 1


# ── get_signal ──────────────────────────────────────────────────


class TestGetSignal:
    async def test_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_signal(
            db_session,
            signal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is None

    async def test_returns_signal_when_owner_matches(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="getsig-hit@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        result = await get_signal(
            db_session, signal_id=signal.id, user_id=user.id,
        )
        assert result is not None
        assert result.id == signal.id

    async def test_returns_none_for_different_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="getsig-other@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        result = await get_signal(
            db_session, signal_id=signal.id, user_id=uuid.uuid4(),
        )
        assert result is None


# ── dismiss_signal ──────────────────────────────────────────────


class TestDismissSignal:
    async def test_returns_none_when_signal_missing(
        self, db_session: AsyncSession,
    ) -> None:
        request = DismissSignalRequest(action_taken="dismissed")
        result = await dismiss_signal(
            db_session,
            signal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            request=request,
        )
        assert result is None

    async def test_dismissed_sets_dismissed_status(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="dismiss@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        request = DismissSignalRequest(action_taken="dismissed")
        result = await dismiss_signal(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
            request=request,
        )
        assert result is not None
        assert result.status == SignalStatus.DISMISSED.value

    async def test_actioned_sets_actioned_status(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="actioned@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        request = DismissSignalRequest(action_taken="actioned")
        result = await dismiss_signal(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
            request=request,
        )
        assert result is not None
        assert result.status == SignalStatus.ACTIONED.value


# ── compare_signals ─────────────────────────────────────────────


class TestCompareSignals:
    async def test_raises_when_fewer_than_two_signals(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="cmp-one@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        with pytest.raises(ValueError, match="At least 2"):
            await compare_signals(
                db_session,
                user_id=user.id,
                signal_ids=[signal.id],
            )

    async def test_raises_when_no_signals_found(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="At least 2"):
            await compare_signals(
                db_session,
                user_id=uuid.uuid4(),
                signal_ids=[uuid.uuid4(), uuid.uuid4()],
            )

    async def test_returns_comparison_with_strongest(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="cmp-ok@test.com",
        )
        s1 = await _make_signal(
            db_session, user=user, dna=dna,
            company_name="WeakCo", title="Weak signal", strength=0.3,
        )
        s2 = await _make_signal(
            db_session, user=user, dna=dna,
            company_name="StrongCo", title="Strong signal", strength=0.9,
        )
        await db_session.commit()

        result = await compare_signals(
            db_session,
            user_id=user.id,
            signal_ids=[s1.id, s2.id],
        )
        assert len(result["signals"]) == 2
        assert result["recommended_signal_id"] == s2.id
        assert "StrongCo" in result["comparison_summary"]


# ── get_opportunity_radar ────────────────────────────────────────


class TestGetOpportunityRadar:
    async def test_returns_empty_structure_without_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_opportunity_radar(
            db_session, user_id=uuid.uuid4(),
        )
        assert result["opportunities"] == []
        assert result["total_opportunities"] == 0
        assert result["top_industries"] == []
        assert result["avg_probability"] == 0.0

    async def test_returns_empty_when_no_opportunities(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="rad-empty@test.com",
        )
        result = await get_opportunity_radar(db_session, user_id=user.id)
        assert result["total_opportunities"] == 0
        assert result["avg_probability"] == 0.0

    async def test_aggregates_opportunities_and_avg_probability(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="rad-agg@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        for prob in (0.4, 0.6, 0.8):
            db_session.add(HiddenOpportunity(
                signal_id=signal.id,
                predicted_role="Role",
                probability=prob,
            ))
        await db_session.commit()

        result = await get_opportunity_radar(db_session, user_id=user.id)
        assert result["total_opportunities"] == 3
        assert result["avg_probability"] == 0.6


# ── get_preferences ─────────────────────────────────────────────


class TestGetPreferences:
    async def test_returns_none_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(
            db_session, user_id=uuid.uuid4(),
        )
        assert result is None

    async def test_returns_none_when_no_preference_row(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="pref-none@test.com",
        )
        result = await get_preferences(db_session, user_id=user.id)
        assert result is None

    async def test_returns_preference_when_set(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="pref-set@test.com",
        )
        pref = HiddenJobMarketPreference(
            career_dna_id=dna.id,
            user_id=user.id,
            min_signal_strength=0.45,
        )
        db_session.add(pref)
        await db_session.commit()

        result = await get_preferences(db_session, user_id=user.id)
        assert result is not None
        assert result.min_signal_strength == 0.45


# ── update_preferences ──────────────────────────────────────────


class TestUpdatePreferences:
    async def test_raises_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        update = HiddenJobMarketPreferenceUpdateRequest()
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=update,
            )

    async def test_creates_new_preference_record(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="upd-new@test.com",
        )
        update = HiddenJobMarketPreferenceUpdateRequest(
            min_signal_strength=0.55,
            max_outreach_per_week=7,
        )
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref is not None
        assert pref.min_signal_strength == 0.55
        assert pref.max_outreach_per_week == 7

    async def test_updates_existing_preference(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="upd-exist@test.com",
        )
        existing = HiddenJobMarketPreference(
            career_dna_id=dna.id,
            user_id=user.id,
            min_signal_strength=0.1,
        )
        db_session.add(existing)
        await db_session.commit()

        update = HiddenJobMarketPreferenceUpdateRequest(
            min_signal_strength=0.66,
        )
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.id == existing.id
        assert pref.min_signal_strength == 0.66

    async def test_converts_enabled_signal_types_to_dict(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="upd-types@test.com",
        )
        update = HiddenJobMarketPreferenceUpdateRequest(
            enabled_signal_types=["funding", "key_hire"],
        )
        pref = await update_preferences(
            db_session, user_id=user.id, update_data=update,
        )
        assert pref.enabled_signal_types == {"types": ["funding", "key_hire"]}


# ── scan_company ────────────────────────────────────────────────


class TestScanCompany:
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA not found"):
            await scan_company(
                db_session,
                user_id=uuid.uuid4(),
                company_name="Acme",
            )

    async def test_happy_path_persists_signals_and_matches(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="scan-ok@test.com",
        )
        fake_analysis = {
            "signals": [
                {
                    "signal_type": "funding",
                    "title": "Series B",
                    "description": "Raised 50M",
                    "strength": 0.8,
                    "source": "TechCrunch",
                    "confidence": 0.7,
                    "expires_in_days": 60,
                },
            ],
            "company_summary": "Growing fast",
        }
        fake_match = {
            "match_score": 0.85,
            "skill_overlap": 0.7,
            "role_relevance": 0.9,
            "explanation": "Fits well",
        }

        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.analyze_company_signals",
            new=AsyncMock(return_value=fake_analysis),
        ), patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.match_signal_to_career_dna",
            new=AsyncMock(return_value=fake_match),
        ), patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.compute_signal_confidence",
            MagicMock(return_value=0.6),
        ):
            signals = await scan_company(
                db_session,
                user_id=user.id,
                company_name="Acme",
                industry="Tech",
            )

        assert len(signals) == 1
        assert signals[0].company_name == "Acme"
        assert signals[0].status == SignalStatus.MATCHED.value
        assert signals[0].confidence_score == 0.6

    async def test_uses_default_when_analysis_is_none(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="scan-none@test.com",
        )
        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.analyze_company_signals",
            new=AsyncMock(return_value=None),
        ):
            signals = await scan_company(
                db_session,
                user_id=user.id,
                company_name="SilentCo",
            )
        assert signals == []

    async def test_filters_by_focus_signal_types(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="scan-filter@test.com",
        )
        fake_analysis = {
            "signals": [
                {"signal_type": "funding", "title": "A", "strength": 0.5},
                {"signal_type": "key_hire", "title": "B", "strength": 0.5},
            ],
        }
        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.analyze_company_signals",
            new=AsyncMock(return_value=fake_analysis),
        ), patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.match_signal_to_career_dna",
            new=AsyncMock(return_value={"match_score": 0.5}),
        ), patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.compute_signal_confidence",
            MagicMock(return_value=0.5),
        ):
            signals = await scan_company(
                db_session,
                user_id=user.id,
                company_name="Acme",
                focus_signal_types=["funding"],
            )
        assert len(signals) == 1
        assert signals[0].signal_type == "funding"

    async def test_empty_signals_list_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="scan-empty@test.com",
        )
        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.analyze_company_signals",
            new=AsyncMock(return_value={"signals": []}),
        ):
            signals = await scan_company(
                db_session,
                user_id=user.id,
                company_name="EmptyCo",
            )
        assert signals == []

    async def test_uses_career_dna_industry_when_none_provided(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="scan-ind@test.com",
            primary_industry="Finance",
        )
        analyze_mock = AsyncMock(return_value={"signals": []})
        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.analyze_company_signals",
            new=analyze_mock,
        ):
            await scan_company(
                db_session, user_id=user.id, company_name="BankCo",
            )
        kwargs = analyze_mock.call_args.kwargs
        assert kwargs["industry"] == "Finance"


# ── generate_outreach ───────────────────────────────────────────


class TestGenerateOutreach:
    async def test_returns_none_when_signal_missing(
        self, db_session: AsyncSession,
    ) -> None:
        request = GenerateOutreachRequest(
            template_type="introduction", tone="professional",
        )
        result = await generate_outreach(
            db_session,
            signal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            request=request,
        )
        assert result is None

    async def test_returns_none_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        # Create a signal under one user, then delete that user's DNA
        # Simpler: request outreach for signal under a user that doesn't
        # have a Career DNA. Because the signal lookup is scoped by
        # user_id, we can't easily reach the "no DNA" branch without
        # tweaking. Instead, just assert the missing-signal branch above.
        user, dna = await _make_user_and_dna(
            db_session, email="out-nodna@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        # Delete the career dna to hit the "no dna" branch
        await db_session.delete(dna)
        await db_session.commit()

        request = GenerateOutreachRequest(
            template_type="introduction", tone="professional",
        )
        result = await generate_outreach(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
            request=request,
        )
        assert result is None

    async def test_happy_path_persists_outreach(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="out-ok@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        fake_outreach = {
            "subject_line": "Hello Acme",
            "body": "Let's connect.",
            "personalization_points": {"signal": "funding"},
            "confidence": 0.75,
        }
        request = GenerateOutreachRequest(
            template_type="introduction", tone="casual",
        )

        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.generate_outreach",
            new=AsyncMock(return_value=fake_outreach),
        ):
            result = await generate_outreach(
                db_session,
                signal_id=signal.id,
                user_id=user.id,
                request=request,
            )
        assert result is not None
        # Verify persistence via a direct query on the session (bypasses
        # identity-map caching of the pre-outreach signal instance).
        from sqlalchemy import select as _select
        rows = (await db_session.execute(
            _select(OutreachTemplate).where(
                OutreachTemplate.signal_id == signal.id,
            ),
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].subject_line == "Hello Acme"
        assert rows[0].tone == "casual"


# ── surface_opportunities ──────────────────────────────────────


class TestSurfaceOpportunities:
    async def test_raises_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA not found"):
            await surface_opportunities(
                db_session,
                user_id=uuid.uuid4(),
            )

    async def test_returns_empty_when_no_active_signals(
        self, db_session: AsyncSession,
    ) -> None:
        user, _ = await _make_user_and_dna(
            db_session, email="surf-none@test.com",
        )
        result = await surface_opportunities(db_session, user_id=user.id)
        assert result == []

    async def test_happy_path_persists_opportunities(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="surf-ok@test.com",
        )
        s1 = await _make_signal(
            db_session, user=user, dna=dna,
            company_name="WeakCo", strength=0.4,
        )
        s2 = await _make_signal(
            db_session, user=user, dna=dna,
            company_name="StrongCo", strength=0.9,
        )
        await db_session.commit()

        fake_opp_result = {
            "opportunities": [
                {
                    "predicted_role": "Staff Engineer",
                    "probability": 0.82,
                    "reasoning": "Growth pattern",
                },
            ],
        }
        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.surface_opportunities",
            new=AsyncMock(return_value=fake_opp_result),
        ):
            signals = await surface_opportunities(
                db_session, user_id=user.id,
            )
        assert len(signals) == 2
        strongest = next(s for s in signals if s.id == s2.id)
        assert len(strongest.hidden_opportunities) == 1
        assert strongest.hidden_opportunities[0].predicted_role == (
            "Staff Engineer"
        )
        weakest = next(s for s in signals if s.id == s1.id)
        assert len(weakest.hidden_opportunities) == 0

    async def test_skips_persist_when_no_opportunities_returned(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="surf-empty-opps@test.com",
        )
        await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        with patch(
            "app.services.hidden_job_market_service"
            ".HiddenJobMarketAnalyzer.surface_opportunities",
            new=AsyncMock(return_value={"opportunities": []}),
        ):
            signals = await surface_opportunities(
                db_session, user_id=user.id,
            )
        assert len(signals) == 1
        assert signals[0].hidden_opportunities == []


# ── _load_signal_with_relations ─────────────────────────────────


class TestLoadSignalWithRelations:
    async def test_loads_signal_with_empty_relations(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="load-sig@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        await db_session.commit()

        loaded = await _load_signal_with_relations(db_session, signal.id)
        assert loaded.id == signal.id
        assert loaded.match_results == []
        assert loaded.outreach_templates == []
        assert loaded.hidden_opportunities == []

    async def test_loads_relationships_eagerly(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(
            db_session, email="load-rel@test.com",
        )
        signal = await _make_signal(db_session, user=user, dna=dna)
        db_session.add(SignalMatchResult(
            signal_id=signal.id, match_score=0.5,
        ))
        db_session.add(OutreachTemplate(
            signal_id=signal.id,
            template_type="introduction",
            tone="professional",
            subject_line="Hi",
            body="Body",
            confidence=0.5,
        ))
        db_session.add(HiddenOpportunity(
            signal_id=signal.id, predicted_role="Eng", probability=0.5,
        ))
        await db_session.commit()

        loaded = await _load_signal_with_relations(db_session, signal.id)
        assert len(loaded.match_results) == 1
        assert len(loaded.outreach_templates) == 1
        assert len(loaded.hidden_opportunities) == 1
