"""
PathForge — Interview Intelligence Service Unit Tests
=====================================================
Service-layer tests for interview_intelligence_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.interview_intelligence import InterviewPrep
from app.models.user import User
from app.services.interview_intelligence_service import (
    _default_company_analysis,
    _format_skills_for_prompt,
    _get_career_summary,
    _get_experience_text,
    _get_growth_text,
    _get_values_text,
    _get_years_experience,
    _store_insights,
    _store_questions,
    _store_star_examples,
    create_interview_prep,
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
    skill_count: int = 2,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Interview Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Backend Engineer",
        primary_industry="Technology",
        seniority_level="mid",
        location="Berlin",
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


def _make_prep(dna: CareerDNA, user_id: uuid.UUID) -> InterviewPrep:
    return InterviewPrep(
        career_dna_id=dna.id,
        user_id=user_id,
        company_name="Acme Corp",
        target_role="Senior Engineer",
        status="completed",
        prep_depth="standard",
        confidence_score=0.7,
    )


# ── Pure helpers ──────────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_no_skills_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_formats_skill_with_proficiency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Go",
            category="technical",
            proficiency_level="expert",
            confidence=0.9,
            source="resume",
        )
        dna.skill_genome = [skill]
        result = _format_skills_for_prompt(dna)
        assert "Go" in result
        assert "expert" in result


class TestGetYearsExperience:
    def test_returns_default_when_no_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        assert _get_years_experience(dna) == 3


class TestGetCareerSummary:
    def test_empty_dna_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        result = _get_career_summary(dna)
        assert result == "No career summary available"

    def test_builds_summary_from_fields(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.primary_role = "Engineer"
        dna.seniority_level = "senior"
        dna.primary_industry = "FinTech"
        result = _get_career_summary(dna)
        assert "Engineer" in result
        assert "senior" in result
        assert "FinTech" in result


class TestGetExperienceText:
    def test_no_blueprint_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.experience_blueprint = None
        assert _get_experience_text(dna) == "No experience data"

    def test_empty_list_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # experience_blueprint is an ORM relationship; None triggers fallback
        result = _get_experience_text(dna)
        assert result == "No experience data"


class TestGetGrowthText:
    def test_no_growth_vector_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.growth_vector = None
        assert _get_growth_text(dna) == "No growth data"

    def test_none_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # growth_vector is an ORM relationship; None triggers fallback
        assert _get_growth_text(dna) == "No growth data"


class TestGetValuesText:
    def test_no_values_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.values_profile = None
        assert _get_values_text(dna) == "No values data"

    def test_none_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # values_profile is an ORM relationship; None triggers fallback
        assert _get_values_text(dna) == "No values data"


class TestDefaultCompanyAnalysis:
    def test_returns_dict_with_required_keys(self) -> None:
        result = _default_company_analysis("Acme", "Engineer")
        assert "company_brief" in result
        assert "interview_format" in result
        assert "confidence_score" in result
        assert "culture_alignment_score" in result
        assert "insights" in result

    def test_includes_company_name_in_brief(self) -> None:
        result = _default_company_analysis("TestCorp", "Analyst")
        assert "TestCorp" in result["company_brief"]


class TestStoreHelpers:
    def test_store_insights_returns_empty_for_empty_input(self) -> None:
        prep = InterviewPrep(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            target_role="Y",
            status="completed",
            prep_depth="standard",
            confidence_score=0.5,
        )
        prep.id = uuid.uuid4()
        result = _store_insights(prep, [])
        assert result == []

    def test_store_insights_creates_records(self) -> None:
        prep = InterviewPrep(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            target_role="Y",
            status="completed",
            prep_depth="standard",
            confidence_score=0.5,
        )
        prep.id = uuid.uuid4()
        insights = _store_insights(prep, [
            {"insight_type": "culture", "title": "Great Culture", "content": "..."},
        ])
        assert len(insights) == 1
        assert insights[0].title == "Great Culture"

    def test_store_questions_creates_records(self) -> None:
        prep = InterviewPrep(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            target_role="Y",
            status="completed",
            prep_depth="standard",
            confidence_score=0.5,
        )
        prep.id = uuid.uuid4()
        questions = _store_questions(prep, [
            {"category": "behavioral", "question_text": "Tell me about yourself"},
        ])
        assert len(questions) == 1
        assert questions[0].question_text == "Tell me about yourself"

    def test_store_star_examples_creates_records(self) -> None:
        prep = InterviewPrep(
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="X",
            target_role="Y",
            status="completed",
            prep_depth="standard",
            confidence_score=0.5,
        )
        prep.id = uuid.uuid4()
        examples = _store_star_examples(prep, [
            {"situation": "S", "task": "T", "action": "A", "result": "R"},
        ])
        assert len(examples) == 1
        assert examples[0].situation == "S"


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["preps"] == []
        assert result["total_preps"] == 0
        assert result["preferences"] is None

    @pytest.mark.asyncio
    async def test_returns_empty_preps_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ii-dash-empty@test.com")
        result = await get_dashboard(db_session, user_id=_user.id)
        assert result["preps"] == []
        assert result["total_preps"] == 0


# ── create_interview_prep ─────────────────────────────────────────


class TestCreateInterviewPrep:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await create_interview_prep(
                db_session,
                user_id=uuid.uuid4(),
                company_name="Acme",
                target_role="Engineer",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_prep(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ii-create@test.com")

        fake_analysis = {
            "company_brief": "Great tech company",
            "interview_format": "4 rounds: tech + culture",
            "confidence_score": 0.75,
            "culture_alignment_score": 0.8,
            "insights": [],
        }
        fake_questions: list = []
        fake_stars: list = []

        with (
            patch(
                "app.services.interview_intelligence_service"
                ".InterviewIntelligenceAnalyzer.analyze_company",
                new=AsyncMock(return_value=fake_analysis),
            ),
            patch(
                "app.services.interview_intelligence_service"
                ".InterviewIntelligenceAnalyzer.generate_questions",
                new=AsyncMock(return_value=fake_questions),
            ),
            patch(
                "app.services.interview_intelligence_service"
                ".InterviewIntelligenceAnalyzer.generate_star_examples",
                new=AsyncMock(return_value=fake_stars),
            ),
        ):
            prep = await create_interview_prep(
                db_session,
                user_id=_user.id,
                company_name="Acme Corp",
                target_role="Senior Engineer",
            )

        assert prep.id is not None
        assert prep.company_name == "Acme Corp"
        assert prep.target_role == "Senior Engineer"
        assert prep.confidence_score == 0.75


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(db_session, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_not_created(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ii-pref-get@test.com")
        result = await get_preferences(db_session, user_id=_user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_creates_and_returns(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ii-pref-update@test.com")
        from app.schemas.interview_intelligence import InterviewPreferenceUpdateRequest

        request = InterviewPreferenceUpdateRequest(default_prep_depth="comprehensive")
        pref = await update_preferences(
            db_session, user_id=_user.id, update_data=request,
        )
        assert pref is not None
        assert pref.id is not None

    @pytest.mark.asyncio
    async def test_update_preferences_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="ii-pref-idem@test.com")
        from app.schemas.interview_intelligence import InterviewPreferenceUpdateRequest

        request = InterviewPreferenceUpdateRequest()
        pref1 = await update_preferences(
            db_session, user_id=_user.id, update_data=request,
        )
        pref2 = await update_preferences(
            db_session, user_id=_user.id, update_data=request,
        )
        assert pref1.id == pref2.id
