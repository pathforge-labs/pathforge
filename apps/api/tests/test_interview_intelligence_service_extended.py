"""
PathForge — Interview Intelligence Service Extended Coverage Tests
====================================================================
Supplementary test suite targeting the uncovered branches in
interview_intelligence_service.py.

Focus areas:
    - Helper branch coverage (list branches of _get_years_experience,
      _get_experience_text, _get_growth_text, _get_values_text).
    - Service methods: get_interview_prep, generate_questions_for_prep,
      generate_star_examples_for_prep, generate_negotiation_script,
      delete_interview_prep, compare_interview_preps,
      _load_prep_with_relations.
    - Edge cases: missing DNA, missing prep, partial comparisons.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.interview_intelligence import (
    InterviewPrep,
    InterviewQuestion,
    STARExample,
)
from app.models.salary_intelligence import SalaryEstimate
from app.models.user import User
from app.schemas.interview_intelligence import InterviewPreferenceUpdateRequest
from app.services.interview_intelligence_service import (
    _get_experience_text,
    _get_growth_text,
    _get_values_text,
    _get_years_experience,
    _load_prep_with_relations,
    compare_interview_preps,
    create_interview_prep,
    delete_interview_prep,
    generate_negotiation_script,
    generate_questions_for_prep,
    generate_star_examples_for_prep,
    get_interview_prep,
    update_preferences,
)

_ANALYZER_PATH = "app.services.interview_intelligence_service.InterviewIntelligenceAnalyzer"


# ── Shared fixtures ───────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
) -> tuple[User, CareerDNA]:
    """Build a user + CareerDNA with minimal skill genome."""
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Ext Tester",
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


async def _make_prep(
    db: AsyncSession,
    user: User,
    dna: CareerDNA,
    *,
    company_name: str = "Acme Corp",
    target_role: str = "Senior Engineer",
    with_questions: bool = False,
) -> InterviewPrep:
    """Persist an InterviewPrep and optionally seed questions."""
    prep = InterviewPrep(
        career_dna_id=dna.id,
        user_id=user.id,
        company_name=company_name,
        target_role=target_role,
        status="completed",
        prep_depth="standard",
        confidence_score=0.7,
        culture_alignment_score=0.6,
        interview_format="4 rounds",
        company_brief="Tech company",
    )
    db.add(prep)
    await db.flush()

    if with_questions:
        question = InterviewQuestion(
            interview_prep_id=prep.id,
            category="behavioral",
            question_text="Tell me about yourself.",
            suggested_answer="I am a backend engineer.",
            frequency_weight=0.8,
            order_index=0,
        )
        db.add(question)
        await db.flush()

    return prep


# ── Helper branch coverage ────────────────────────────────────────


def _fake_dna(**attrs: object) -> object:
    """Build a Python object that duck-types as CareerDNA for helper tests.

    SQLAlchemy managed relationship attributes reject raw list assignment
    on real CareerDNA instances, so the helper functions are exercised
    against a plain SimpleNamespace whose attribute set matches the
    fields each helper accesses.
    """
    base: dict[str, object] = {
        "experience_blueprint": None,
        "growth_vector": None,
        "values_profile": None,
        "skill_genome": None,
        "primary_role": None,
        "seniority_level": None,
        "primary_industry": None,
    }
    base.update(attrs)
    return SimpleNamespace(**base)


class TestYearsExperienceListBranch:
    """Cover lines 74-77: the list-typed experience_blueprint branch."""

    def test_list_with_two_entries_returns_four_years(self) -> None:
        dna = _fake_dna(experience_blueprint=[
            SimpleNamespace(role_title="A", company_context="X"),
            SimpleNamespace(role_title="B", company_context="Y"),
        ])
        assert _get_years_experience(dna) == 4  # type: ignore[arg-type]

    def test_list_with_one_entry_returns_two_years(self) -> None:
        dna = _fake_dna(experience_blueprint=[
            SimpleNamespace(role_title="A", company_context="X"),
        ])
        assert _get_years_experience(dna) == 2  # type: ignore[arg-type]

    def test_empty_list_falls_through_to_default(self) -> None:
        dna = _fake_dna(experience_blueprint=[])
        assert _get_years_experience(dna) == 3  # type: ignore[arg-type]


class TestExperienceTextListBranch:
    """Cover lines 97-105."""

    def test_list_formats_up_to_five_entries(self) -> None:
        dna = _fake_dna(experience_blueprint=[
            SimpleNamespace(role_title=f"Role{i}", company_context=f"Co{i}")
            for i in range(7)
        ])
        result = _get_experience_text(dna)  # type: ignore[arg-type]
        assert "Role0 at Co0" in result
        assert "Role4 at Co4" in result
        assert "Role5" not in result
        assert "Role6" not in result

    def test_list_missing_attributes_falls_back_per_item(self) -> None:
        dna = _fake_dna(experience_blueprint=[SimpleNamespace()])
        result = _get_experience_text(dna)  # type: ignore[arg-type]
        assert "Unknown role at Unknown" in result

    def test_non_list_truthy_returns_fallback(self) -> None:
        # A non-list truthy value hits the final fallback at line 105.
        dna = _fake_dna(experience_blueprint=SimpleNamespace(role_title="A"))
        assert _get_experience_text(dna) == "No experience data"  # type: ignore[arg-type]


class TestGrowthTextListBranch:
    """Cover lines 112-120."""

    def test_list_formats_direction_and_target(self) -> None:
        dna = _fake_dna(growth_vector=[
            SimpleNamespace(direction="upward", target_role="Staff"),
            SimpleNamespace(direction="lateral", target_role="EM"),
        ])
        result = _get_growth_text(dna)  # type: ignore[arg-type]
        assert "Direction: upward" in result
        assert "Target: Staff" in result
        assert "Direction: lateral" in result

    def test_list_missing_attributes_fallbacks(self) -> None:
        dna = _fake_dna(growth_vector=[SimpleNamespace()])
        result = _get_growth_text(dna)  # type: ignore[arg-type]
        assert "Direction: unknown" in result
        assert "Target: unknown" in result

    def test_non_list_truthy_returns_fallback(self) -> None:
        dna = _fake_dna(growth_vector=SimpleNamespace(direction="up"))
        assert _get_growth_text(dna) == "No growth data"  # type: ignore[arg-type]

    def test_truncates_to_five_entries(self) -> None:
        dna = _fake_dna(growth_vector=[
            SimpleNamespace(direction=f"d{i}", target_role=f"t{i}")
            for i in range(8)
        ])
        result = _get_growth_text(dna)  # type: ignore[arg-type]
        assert "d0" in result
        assert "d4" in result
        assert "d5" not in result


class TestValuesTextListBranch:
    """Cover lines 127-135."""

    def test_list_formats_name_and_priority(self) -> None:
        dna = _fake_dna(values_profile=[
            SimpleNamespace(value_name="autonomy", priority_rank=1),
            SimpleNamespace(value_name="impact", priority_rank=2),
        ])
        result = _get_values_text(dna)  # type: ignore[arg-type]
        assert "autonomy (priority: 1)" in result
        assert "impact (priority: 2)" in result

    def test_list_missing_attributes_fallbacks(self) -> None:
        dna = _fake_dna(values_profile=[SimpleNamespace()])
        result = _get_values_text(dna)  # type: ignore[arg-type]
        assert "unknown (priority: 0)" in result

    def test_non_list_truthy_returns_fallback(self) -> None:
        dna = _fake_dna(values_profile=SimpleNamespace(value_name="x"))
        assert _get_values_text(dna) == "No values data"  # type: ignore[arg-type]

    def test_truncates_to_five_entries(self) -> None:
        dna = _fake_dna(values_profile=[
            SimpleNamespace(value_name=f"v{i}", priority_rank=i)
            for i in range(7)
        ])
        result = _get_values_text(dna)  # type: ignore[arg-type]
        assert "v0" in result
        assert "v4" in result
        assert "v5" not in result


# ── create_interview_prep — analyzer None fallback (line 266) ─────


class TestCreateInterviewPrepFallbacks:
    @pytest.mark.asyncio
    async def test_falls_back_to_default_when_analyzer_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        """Line 266: analysis is None → _default_company_analysis used."""
        user, _dna = await _make_dna(db_session, email="ext-fallback@test.com")

        with (
            patch(
                f"{_ANALYZER_PATH}.analyze_company",
                new=AsyncMock(return_value=None),
            ),
            patch(
                f"{_ANALYZER_PATH}.generate_questions",
                new=AsyncMock(return_value=[
                    {
                        "category": "behavioral",
                        "question_text": "Q1",
                        "frequency_weight": 0.7,
                    },
                ]),
            ),
            patch(
                f"{_ANALYZER_PATH}.generate_star_examples",
                new=AsyncMock(return_value=[
                    {
                        "situation": "S",
                        "task": "T",
                        "action": "A",
                        "result": "R",
                    },
                ]),
            ),
        ):
            prep = await create_interview_prep(
                db_session,
                user_id=user.id,
                company_name="FallbackCo",
                target_role="Engineer",
            )

        # Confidence comes from the default analysis (0.3)
        assert prep.confidence_score == 0.3
        assert "FallbackCo" in (prep.company_brief or "")
        assert len(prep.questions) == 1
        assert len(prep.star_examples) == 1

    @pytest.mark.asyncio
    async def test_quick_depth_uses_smaller_limits(
        self, db_session: AsyncSession,
    ) -> None:
        """Covers lines 312, 317, 322 where quick depth branches."""
        user, _dna = await _make_dna(db_session, email="ext-quick@test.com")

        analysis = {
            "company_brief": "Brief",
            "interview_format": "2 rounds",
            "confidence_score": 0.5,
            "culture_alignment_score": 0.6,
            "insights": [
                {
                    "insight_type": "format",
                    "title": "Format",
                    "content": None,
                    "summary": "Quick",
                    "confidence": 0.7,
                },
            ],
        }

        gen_q = AsyncMock(return_value=[])
        gen_s = AsyncMock(return_value=[])

        with (
            patch(
                f"{_ANALYZER_PATH}.analyze_company",
                new=AsyncMock(return_value=analysis),
            ),
            patch(f"{_ANALYZER_PATH}.generate_questions", new=gen_q),
            patch(f"{_ANALYZER_PATH}.generate_star_examples", new=gen_s),
        ):
            prep = await create_interview_prep(
                db_session,
                user_id=user.id,
                company_name="QuickCo",
                target_role="Dev",
                prep_depth="quick",
            )

        gen_q.assert_awaited_once()
        _, gen_q_kwargs = gen_q.call_args
        assert gen_q_kwargs["max_questions"] == 15

        gen_s.assert_awaited_once()
        _, gen_s_kwargs = gen_s.call_args
        assert gen_s_kwargs["max_examples"] == 5

        assert prep.prep_depth == "quick"
        assert len(prep.insights) == 1


# ── get_interview_prep (lines 385-398) ────────────────────────────


class TestGetInterviewPrep:
    @pytest.mark.asyncio
    async def test_returns_prep_with_relations(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-get@test.com")
        prep = await _make_prep(
            db_session, user, dna, with_questions=True,
        )

        result = await get_interview_prep(
            db_session, prep_id=prep.id, user_id=user.id,
        )
        assert result is not None
        assert result.id == prep.id
        assert len(result.questions) == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ext-get-miss@test.com")
        result = await get_interview_prep(
            db_session, prep_id=uuid.uuid4(), user_id=user.id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_other_users_prep(
        self, db_session: AsyncSession,
    ) -> None:
        user_a, dna_a = await _make_dna(db_session, email="ext-get-a@test.com")
        user_b, _dna_b = await _make_dna(db_session, email="ext-get-b@test.com")
        prep = await _make_prep(db_session, user_a, dna_a)

        result = await get_interview_prep(
            db_session, prep_id=prep.id, user_id=user_b.id,
        )
        assert result is None


# ── generate_questions_for_prep (lines 410-435) ───────────────────


class TestGenerateQuestionsForPrep:
    @pytest.mark.asyncio
    async def test_returns_none_when_prep_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ext-gq-miss@test.com")
        result = await generate_questions_for_prep(
            db_session,
            prep_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_career_dna_missing(
        self, db_session: AsyncSession,
    ) -> None:
        """Prep exists but Career DNA lookup yields nothing for the user.

        We patch the helper to simulate the DNA-missing branch, because
        cascade deletion of the DNA would also remove the prep.
        """
        user, dna = await _make_dna(db_session, email="ext-gq-nodna@test.com")
        prep = await _make_prep(db_session, user, dna)

        dna_mock = AsyncMock(return_value=None)
        with patch(
            "app.services.interview_intelligence_service."
            "_get_career_dna_with_context",
            new=dna_mock,
        ):
            result = await generate_questions_for_prep(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_happy_path_adds_questions(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-gq-ok@test.com")
        prep = await _make_prep(
            db_session, user, dna, with_questions=False,
        )

        gen_q = AsyncMock(return_value=[
            {
                "category": "technical",
                "question_text": "Explain Python GIL.",
                "frequency_weight": 0.9,
                "order_index": 1,
            },
            {
                "category": "behavioral",
                "question_text": "Describe a conflict.",
                "frequency_weight": 0.8,
                "order_index": 2,
            },
        ])
        with patch(f"{_ANALYZER_PATH}.generate_questions", new=gen_q):
            result = await generate_questions_for_prep(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
                category_filter="technical",
                max_questions=10,
            )

        assert result is not None
        gen_q.assert_awaited_once()
        _, call_kwargs = gen_q.call_args
        assert call_kwargs["category_filter"] == "technical"
        assert call_kwargs["max_questions"] == 10

        # Query the persisted rows directly to verify the store-and-commit path.
        from sqlalchemy import select as _select

        rows = await db_session.execute(
            _select(InterviewQuestion).where(
                InterviewQuestion.interview_prep_id == prep.id,
            ),
        )
        questions = list(rows.scalars().all())
        assert len(questions) >= 2
        assert any(q.question_text == "Explain Python GIL." for q in questions)


# ── generate_star_examples_for_prep (lines 446-481) ───────────────


class TestGenerateStarExamplesForPrep:
    @pytest.mark.asyncio
    async def test_returns_none_when_prep_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ext-gs-miss@test.com")
        result = await generate_star_examples_for_prep(
            db_session,
            prep_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_career_dna_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-gs-nodna@test.com")
        prep = await _make_prep(db_session, user, dna)

        dna_mock = AsyncMock(return_value=None)
        with patch(
            "app.services.interview_intelligence_service."
            "_get_career_dna_with_context",
            new=dna_mock,
        ):
            result = await generate_star_examples_for_prep(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_builds_question_context_from_existing_questions(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-gs-ctx@test.com")
        prep = await _make_prep(
            db_session, user, dna, with_questions=True,
        )

        gen_s = AsyncMock(return_value=[
            {
                "situation": "S1",
                "task": "T1",
                "action": "A1",
                "result": "R1",
                "relevance_score": 0.85,
            },
        ])
        with patch(f"{_ANALYZER_PATH}.generate_star_examples", new=gen_s):
            result = await generate_star_examples_for_prep(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
                max_examples=3,
            )

        assert result is not None
        gen_s.assert_awaited_once()
        _, call_kwargs = gen_s.call_args
        # Question context should include the seeded question
        assert "Tell me about yourself" in call_kwargs["question_context"]
        assert call_kwargs["max_examples"] == 3

        # Verify persistence independently of the reload collection
        from sqlalchemy import select as _select

        rows = await db_session.execute(
            _select(STARExample).where(
                STARExample.interview_prep_id == prep.id,
            ),
        )
        examples = list(rows.scalars().all())
        assert len(examples) >= 1
        assert any(e.situation == "S1" for e in examples)

    @pytest.mark.asyncio
    async def test_default_question_context_when_no_questions(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-gs-empty@test.com")
        prep = await _make_prep(db_session, user, dna, with_questions=False)

        gen_s = AsyncMock(return_value=[])
        with patch(f"{_ANALYZER_PATH}.generate_star_examples", new=gen_s):
            result = await generate_star_examples_for_prep(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
            )

        assert result is not None
        _, call_kwargs = gen_s.call_args
        assert call_kwargs["question_context"] == "No specific questions provided."


# ── generate_negotiation_script (lines 493-544) ───────────────────


class TestGenerateNegotiationScript:
    @pytest.mark.asyncio
    async def test_raises_when_prep_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ext-neg-miss@test.com")
        with pytest.raises(ValueError, match="Interview prep not found"):
            await generate_negotiation_script(
                db_session,
                prep_id=uuid.uuid4(),
                user_id=user.id,
            )

    @pytest.mark.asyncio
    async def test_raises_when_career_dna_missing(
        self, db_session: AsyncSession,
    ) -> None:
        """Career DNA lookup within generate_negotiation_script returns None.

        A cascade-delete of the DNA would also drop the prep, so we patch
        the helper directly to simulate the None-after-prep-found branch.
        """
        user, dna = await _make_dna(db_session, email="ext-neg-nodna@test.com")
        prep = await _make_prep(db_session, user, dna)

        dna_mock = AsyncMock(return_value=None)
        with patch(
            "app.services.interview_intelligence_service."
            "_get_career_dna_with_context",
            new=dna_mock,
        ), pytest.raises(ValueError, match="Career DNA not found"):
            await generate_negotiation_script(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
            )

    @pytest.mark.asyncio
    async def test_attaches_prep_context_without_salary_estimate(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-neg-ok@test.com")
        prep = await _make_prep(db_session, user, dna)

        merge_fn = AsyncMock(return_value="merged-salary-blob")
        # merge_salary_data is sync in the analyzer; patch with a plain callable
        with (
            patch(
                f"{_ANALYZER_PATH}.merge_salary_data",
                return_value="merged-salary-blob",
            ),
            patch(
                f"{_ANALYZER_PATH}.generate_negotiation_script",
                new=AsyncMock(return_value={
                    "script": "Negotiate firmly",
                    "anchor": 90000,
                }),
            ),
        ):
            script = await generate_negotiation_script(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
                target_salary=95000,
                currency="EUR",
            )

        assert script["interview_prep_id"] == str(prep.id)
        assert script["company_name"] == prep.company_name
        assert script["target_role"] == prep.target_role
        assert script["script"] == "Negotiate firmly"
        _ = merge_fn  # appease unused-warning linter

    @pytest.mark.asyncio
    async def test_includes_latest_salary_estimate(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-neg-sal@test.com")
        prep = await _make_prep(db_session, user, dna)

        estimate = SalaryEstimate(
            career_dna_id=dna.id,
            role_title="Backend Engineer",
            location="Berlin",
            seniority_level="mid",
            industry="Technology",
            estimated_min=70000,
            estimated_max=95000,
            estimated_median=82000,
            currency="EUR",
            confidence=0.75,
            data_points_count=50,
        )
        db_session.add(estimate)
        await db_session.flush()

        merge_fn = patch(
            f"{_ANALYZER_PATH}.merge_salary_data",
            return_value="merged",
        )
        script_fn = patch(
            f"{_ANALYZER_PATH}.generate_negotiation_script",
            new=AsyncMock(return_value={"script": "Anchored high"}),
        )
        with merge_fn as merge_mock, script_fn:
            script = await generate_negotiation_script(
                db_session,
                prep_id=prep.id,
                user_id=user.id,
            )

        assert script["script"] == "Anchored high"
        # Confirm the latest salary estimate was forwarded to merge_salary_data
        _, call_kwargs = merge_mock.call_args
        estimates_arg = call_kwargs["salary_estimates"]
        assert len(estimates_arg) == 1
        assert estimates_arg[0]["role_title"] == "Backend Engineer"
        assert estimates_arg[0]["estimated_median"] == 82000


# ── delete_interview_prep (lines 554-560) ─────────────────────────


class TestDeleteInterviewPrep:
    @pytest.mark.asyncio
    async def test_returns_false_when_prep_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="ext-del-miss@test.com")
        result = await delete_interview_prep(
            db_session,
            prep_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_deletes_and_returns_true(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-del-ok@test.com")
        prep = await _make_prep(db_session, user, dna)

        ok = await delete_interview_prep(
            db_session,
            prep_id=prep.id,
            user_id=user.id,
        )
        assert ok is True

        # Confirm it is actually gone
        result = await get_interview_prep(
            db_session, prep_id=prep.id, user_id=user.id,
        )
        assert result is None


# ── compare_interview_preps (lines 570-603) ───────────────────────


class TestCompareInterviewPreps:
    @pytest.mark.asyncio
    async def test_raises_when_career_dna_missing(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA not found"):
            await compare_interview_preps(
                db_session,
                user_id=uuid.uuid4(),
                prep_ids=[uuid.uuid4(), uuid.uuid4()],
            )

    @pytest.mark.asyncio
    async def test_raises_when_less_than_two_valid_preps(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-cmp-one@test.com")
        prep = await _make_prep(db_session, user, dna)

        with pytest.raises(ValueError, match="At least 2 valid"):
            await compare_interview_preps(
                db_session,
                user_id=user.id,
                prep_ids=[prep.id, uuid.uuid4()],
            )

    @pytest.mark.asyncio
    async def test_returns_ranking_for_two_preps(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-cmp-ok@test.com")
        prep_a = await _make_prep(
            db_session, user, dna, company_name="Acme",
        )
        prep_b = await _make_prep(
            db_session, user, dna, company_name="Beta",
        )

        # Seed one STAR example to exercise star_examples_count branch
        star = STARExample(
            interview_prep_id=prep_a.id,
            situation="S",
            task="T",
            action="A",
            result="R",
            relevance_score=0.7,
        )
        db_session.add(star)
        await db_session.flush()

        compare_mock = AsyncMock(return_value={
            "ranking": [
                {"id": str(prep_a.id), "rank": 1},
                {"id": str(prep_b.id), "rank": 2},
            ],
            "comparison_summary": "Prep A stronger",
        })
        with patch(f"{_ANALYZER_PATH}.compare_preps", new=compare_mock):
            result = await compare_interview_preps(
                db_session,
                user_id=user.id,
                prep_ids=[prep_a.id, prep_b.id],
            )

        assert len(result["preps"]) == 2
        assert result["comparison_summary"] == "Prep A stronger"
        assert len(result["ranking"]) == 2

    @pytest.mark.asyncio
    async def test_ignores_missing_prep_ids(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-cmp-skip@test.com")
        prep_a = await _make_prep(db_session, user, dna, company_name="Acme")
        prep_b = await _make_prep(db_session, user, dna, company_name="Beta")

        compare_mock = AsyncMock(return_value={
            "ranking": [],
            "comparison_summary": "",
        })
        with patch(f"{_ANALYZER_PATH}.compare_preps", new=compare_mock):
            result = await compare_interview_preps(
                db_session,
                user_id=user.id,
                # Include one unknown id that must be silently skipped
                prep_ids=[prep_a.id, uuid.uuid4(), prep_b.id],
            )

        assert len(result["preps"]) == 2


# ── update_preferences raises on missing DNA (line 636) ───────────


class TestUpdatePreferencesEdge:
    @pytest.mark.asyncio
    async def test_raises_when_career_dna_missing(
        self, db_session: AsyncSession,
    ) -> None:
        request = InterviewPreferenceUpdateRequest(
            default_prep_depth="quick",
        )
        with pytest.raises(ValueError, match="Career DNA not found"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=request,
            )


# ── _load_prep_with_relations direct coverage ─────────────────────


class TestLoadPrepWithRelations:
    @pytest.mark.asyncio
    async def test_loads_all_relations(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_dna(db_session, email="ext-load@test.com")
        prep = await _make_prep(
            db_session, user, dna, with_questions=True,
        )
        loaded = await _load_prep_with_relations(db_session, prep.id)
        assert loaded.id == prep.id
        assert isinstance(loaded.questions, list)
        assert len(loaded.questions) == 1
        # Relationships should be eagerly loaded without triggering N+1
        assert isinstance(loaded.insights, list)
        assert isinstance(loaded.star_examples, list)
