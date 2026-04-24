"""Unit tests for Hidden Job Market service layer."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.hidden_job_market import CompanySignal
from app.models.user import User
from app.schemas.hidden_job_market import (
    DismissSignalRequest,
    HiddenJobMarketPreferenceUpdateRequest,
)
from app.services.hidden_job_market_service import (
    _default_signal_analysis,
    _format_skills_for_prompt,
    _get_years_experience,
    _store_match_result,
    _store_opportunities,
    _store_outreach,
    compare_signals,
    dismiss_signal,
    get_dashboard,
    get_opportunity_radar,
    get_preferences,
    get_signal,
    update_preferences,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


async def _make_user_and_dna(
    db: AsyncSession, *, email: str,
) -> tuple[User, CareerDNA]:
    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="HJM Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="senior",
    )
    db.add(dna)
    await db.flush()
    return user, dna


async def _make_signal(
    db: AsyncSession,
    *,
    career_dna_id: uuid.UUID,
    user_id: uuid.UUID,
    company: str = "TechCorp",
    strength: float = 0.75,
    status: str = "detected",
) -> CompanySignal:
    signal = CompanySignal(
        career_dna_id=career_dna_id,
        user_id=user_id,
        company_name=company,
        signal_type="funding",
        title=f"{company} Series B",
        description="Raised $50M.",
        strength=strength,
        status=status,
        confidence_score=0.70,
        source="crunchbase",
    )
    db.add(signal)
    await db.flush()
    return signal


# ── Pure Helper Tests ─────────────────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_no_skills_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_formats_skills_with_proficiency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Python",
            category="technical",
            proficiency_level="expert",
            confidence=0.90,
            source="resume",
        )
        dna.skill_genome = [skill]
        result = _format_skills_for_prompt(dna)
        assert "Python" in result
        assert "expert" in result

    def test_multiple_skills_comma_separated(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skills = []
        for name, level in [("Go", "advanced"), ("Rust", "intermediate")]:
            s = SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name=name,
                category="technical",
                proficiency_level=level,
                confidence=0.80,
                source="resume",
            )
            skills.append(s)
        dna.skill_genome = skills
        result = _format_skills_for_prompt(dna)
        assert "Go" in result
        assert "Rust" in result
        assert "," in result


class TestGetYearsExperience:
    def test_returns_default_3_when_no_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        assert _get_years_experience(dna) == 3

    def test_uses_total_years_from_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = MagicMock()
        blueprint.total_years = 8
        dna.experience_blueprint = blueprint
        assert _get_years_experience(dna) == 8

    def test_clamps_to_minimum_1(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = MagicMock()
        blueprint.total_years = 0
        dna.experience_blueprint = blueprint
        assert _get_years_experience(dna) == 1


class TestDefaultSignalAnalysis:
    def test_returns_empty_signals(self) -> None:
        result = _default_signal_analysis("Acme Corp")
        assert result["signals"] == []

    def test_summary_contains_company_name(self) -> None:
        result = _default_signal_analysis("Acme Corp")
        assert "Acme Corp" in result["company_summary"]


class TestStoreMatchResult:
    def test_creates_match_result_from_data(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="Acme",
            signal_type="funding",
            title="Series A",
            strength=0.7,
            status="detected",
            confidence_score=0.6,
        )
        signal.id = uuid.uuid4()

        data = {
            "match_score": 0.80,
            "skill_overlap": 0.75,
            "role_relevance": 0.85,
            "explanation": "Strong backend match.",
        }
        result = _store_match_result(signal, data)
        assert result.signal_id == signal.id
        assert result.match_score == 0.80
        assert result.skill_overlap == 0.75
        assert result.role_relevance == 0.85
        assert result.explanation == "Strong backend match."

    def test_handles_missing_fields_with_defaults(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            signal_type="key_hire",
            title="CTO hired",
            strength=0.5,
            status="detected",
            confidence_score=0.5,
        )
        signal.id = uuid.uuid4()
        result = _store_match_result(signal, {})
        assert result.match_score == 0.0
        assert result.skill_overlap == 0.0
        assert result.role_relevance == 0.0


class TestStoreOutreach:
    def test_creates_outreach_template(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="Beta",
            signal_type="funding",
            title="Seed Round",
            strength=0.6,
            status="matched",
            confidence_score=0.6,
        )
        signal.id = uuid.uuid4()

        data = {
            "subject_line": "Hello from a potential hire",
            "body": "Dear Hiring Manager...",
            "confidence": 0.72,
        }
        result = _store_outreach(signal, data, "introduction", "professional")
        assert result.signal_id == signal.id
        assert result.template_type == "introduction"
        assert result.tone == "professional"
        assert result.subject_line == "Hello from a potential hire"
        assert result.confidence == 0.72

    def test_fallback_subject_when_missing(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            signal_type="funding",
            title="T",
            strength=0.5,
            status="detected",
            confidence_score=0.5,
        )
        signal.id = uuid.uuid4()
        result = _store_outreach(signal, {}, "introduction", "casual")
        assert result.subject_line == "Connection opportunity"


class TestStoreOpportunities:
    def test_creates_opportunity_records(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="GrowCo",
            signal_type="revenue_growth",
            title="50% growth",
            strength=0.85,
            status="matched",
            confidence_score=0.75,
        )
        signal.id = uuid.uuid4()

        opps_data = [
            {
                "predicted_role": "Senior Engineer",
                "predicted_seniority": "senior",
                "probability": 0.70,
                "reasoning": "Strong revenue growth.",
            },
            {
                "predicted_role": "Staff Engineer",
                "probability": 0.55,
                "reasoning": "Expansion phase.",
            },
        ]
        results = _store_opportunities(signal, opps_data)
        assert len(results) == 2
        assert results[0].predicted_role == "Senior Engineer"
        assert results[0].probability == 0.70
        assert results[1].predicted_role == "Staff Engineer"

    def test_empty_list_returns_empty(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            signal_type="funding",
            title="T",
            strength=0.5,
            status="detected",
            confidence_score=0.5,
        )
        signal.id = uuid.uuid4()
        results = _store_opportunities(signal, [])
        assert results == []

    def test_fallback_role_when_missing(self) -> None:
        signal = CompanySignal(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            signal_type="funding",
            title="T",
            strength=0.5,
            status="detected",
            confidence_score=0.5,
        )
        signal.id = uuid.uuid4()
        results = _store_opportunities(signal, [{"probability": 0.5}])
        assert results[0].predicted_role == "Unknown role"


# ── DB-Level Service Tests ────────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_empty_when_no_career_dna(self, db_session: AsyncSession) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["signals"] == []
        assert result["preferences"] is None
        assert result["total_signals"] == 0
        assert result["active_signals"] == 0

    @pytest.mark.asyncio
    async def test_returns_signals_when_career_dna_exists(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-dash@test.com")
        await _make_signal(db_session, career_dna_id=dna.id, user_id=user.id)
        result = await get_dashboard(db_session, user_id=user.id)
        assert result["total_signals"] == 1
        assert result["active_signals"] == 1

    @pytest.mark.asyncio
    async def test_counts_dismissed_signals(self, db_session: AsyncSession) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-dismissed@test.com")
        await _make_signal(
            db_session,
            career_dna_id=dna.id,
            user_id=user.id,
            status="dismissed",
        )
        result = await get_dashboard(db_session, user_id=user.id)
        assert result["dismissed_signals"] == 1
        assert result["active_signals"] == 0


class TestGetSignal:
    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_signal(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_signal(
            db_session,
            signal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-sig-owner@test.com")
        signal = await _make_signal(db_session, career_dna_id=dna.id, user_id=user.id)
        result = await get_signal(
            db_session,
            signal_id=signal.id,
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_signal_for_correct_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-sig-found@test.com")
        signal = await _make_signal(db_session, career_dna_id=dna.id, user_id=user.id)
        result = await get_signal(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
        )
        assert result is not None
        assert result.id == signal.id


class TestDismissSignal:
    @pytest.mark.asyncio
    async def test_returns_none_when_signal_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        req = DismissSignalRequest(action_taken="dismissed")
        result = await dismiss_signal(
            db_session,
            signal_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            request=req,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_sets_dismissed_status(self, db_session: AsyncSession) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-dismiss@test.com")
        signal = await _make_signal(db_session, career_dna_id=dna.id, user_id=user.id)
        req = DismissSignalRequest(action_taken="dismissed")
        result = await dismiss_signal(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
            request=req,
        )
        assert result is not None
        assert result.status == "dismissed"

    @pytest.mark.asyncio
    async def test_sets_actioned_status(self, db_session: AsyncSession) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-action@test.com")
        signal = await _make_signal(db_session, career_dna_id=dna.id, user_id=user.id)
        req = DismissSignalRequest(action_taken="actioned")
        result = await dismiss_signal(
            db_session,
            signal_id=signal.id,
            user_id=user.id,
            request=req,
        )
        assert result is not None
        assert result.status == "actioned"


class TestCompareSignals:
    @pytest.mark.asyncio
    async def test_raises_when_fewer_than_2_valid_signals(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="2 valid signals"):
            await compare_signals(
                db_session,
                user_id=uuid.uuid4(),
                signal_ids=[uuid.uuid4(), uuid.uuid4()],
            )

    @pytest.mark.asyncio
    async def test_compares_two_valid_signals(self, db_session: AsyncSession) -> None:
        user, dna = await _make_user_and_dna(db_session, email="hjm-compare@test.com")
        s1 = await _make_signal(
            db_session, career_dna_id=dna.id, user_id=user.id,
            company="AlphaCo", strength=0.85,
        )
        s2 = await _make_signal(
            db_session, career_dna_id=dna.id, user_id=user.id,
            company="BetaCo", strength=0.65,
        )
        result = await compare_signals(
            db_session,
            user_id=user.id,
            signal_ids=[s1.id, s2.id],
        )
        assert len(result["signals"]) == 2
        assert result["recommended_signal_id"] == s1.id
        assert "AlphaCo" in result["comparison_summary"]


class TestGetOpportunityRadar:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_opportunity_radar(db_session, user_id=uuid.uuid4())
        assert result["opportunities"] == []
        assert result["total_opportunities"] == 0
        assert result["avg_probability"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_empty_when_career_dna_has_no_signals(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(db_session, email="hjm-radar@test.com")
        result = await get_opportunity_radar(db_session, user_id=user.id)
        assert result["total_opportunities"] == 0


class TestGetPreferences:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(db_session, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_preferences_set(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(db_session, email="hjm-pref-empty@test.com")
        result = await get_preferences(db_session, user_id=user.id)
        assert result is None


class TestUpdatePreferences:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        update = HiddenJobMarketPreferenceUpdateRequest()
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=update,
            )

    @pytest.mark.asyncio
    async def test_creates_preferences(self, db_session: AsyncSession) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="hjm-pref-create@test.com",
        )
        update = HiddenJobMarketPreferenceUpdateRequest(min_signal_strength=0.6)
        pref = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=update,
        )
        assert pref is not None
        assert pref.min_signal_strength == 0.6

    @pytest.mark.asyncio
    async def test_update_is_idempotent(self, db_session: AsyncSession) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="hjm-pref-idem@test.com",
        )
        update = HiddenJobMarketPreferenceUpdateRequest()
        pref1 = await update_preferences(db_session, user_id=user.id, update_data=update)
        pref2 = await update_preferences(db_session, user_id=user.id, update_data=update)
        assert pref1.id == pref2.id
