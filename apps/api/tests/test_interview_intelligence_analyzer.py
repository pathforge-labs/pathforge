"""
Unit tests for InterviewIntelligenceAnalyzer.

Covers:
  - 4 static helpers (compute_interview_confidence, calculate_culture_alignment,
    validate_star_structure, merge_salary_data)
  - 5 async LLM methods (analyze_company, generate_questions,
    generate_star_examples, generate_negotiation_script, compare_preps)
  - 4 private clamping validators (_clamp_company_analysis, _clamp_questions,
    _clamp_star_examples, _clamp_negotiation_script)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.interview_intelligence_analyzer import (
    MAX_INTERVIEW_CONFIDENCE,
    VALID_DIFFICULTY_LEVELS,
    VALID_INSIGHT_TYPES,
    VALID_QUESTION_CATEGORIES,
    InterviewIntelligenceAnalyzer,
    _clamp_company_analysis,
    _clamp_negotiation_script,
    _clamp_questions,
    _clamp_star_examples,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize(module: str = "app.ai.interview_intelligence_analyzer.sanitize_user_text"):
    return patch(module, side_effect=_sanitize_passthrough)


def _patch_complete_json(return_value):
    return patch(
        "app.ai.interview_intelligence_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_interview_confidence ───────────────────────────────


class TestComputeInterviewConfidence:
    def test_basic_weighted_formula(self) -> None:
        # 0.40*0.8 + 0.30*0.6 + 0.30*0.7 = 0.32 + 0.18 + 0.21 = 0.71
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=0.8,
            career_dna_completeness=0.6,
            data_quality_factor=0.7,
        )
        assert abs(result - 0.710) < 0.001

    def test_capped_at_max_confidence(self) -> None:
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=1.0,
            career_dna_completeness=1.0,
            data_quality_factor=1.0,
        )
        assert result == MAX_INTERVIEW_CONFIDENCE

    def test_llm_confidence_capped_at_max_before_weighting(self) -> None:
        result_high = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=99.0,
            career_dna_completeness=0.0,
            data_quality_factor=0.0,
        )
        result_cap = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=MAX_INTERVIEW_CONFIDENCE,
            career_dna_completeness=0.0,
            data_quality_factor=0.0,
        )
        assert result_high == result_cap

    def test_zero_inputs_returns_zero(self) -> None:
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=0.0,
            career_dna_completeness=0.0,
            data_quality_factor=0.0,
        )
        assert result == 0.0

    def test_negative_inputs_clamped_to_zero(self) -> None:
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=-5.0,
            career_dna_completeness=-1.0,
            data_quality_factor=-2.0,
        )
        assert result == 0.0

    def test_default_factors_are_half(self) -> None:
        # defaults: data_quality=0.5, career_dna=0.5
        # 0.40*0.6 + 0.30*0.5 + 0.30*0.5 = 0.24 + 0.15 + 0.15 = 0.54
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=0.6,
        )
        assert abs(result - 0.540) < 0.001

    def test_result_is_rounded_to_3_decimals(self) -> None:
        result = InterviewIntelligenceAnalyzer.compute_interview_confidence(
            llm_confidence=0.333,
            career_dna_completeness=0.333,
            data_quality_factor=0.333,
        )
        assert result == round(result, 3)


# ── calculate_culture_alignment ────────────────────────────────


class TestCalculateCultureAlignment:
    def test_basic_weighted_formula(self) -> None:
        # 0.60*0.8 + 0.40*(3/5) = 0.48 + 0.24 = 0.72
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=0.8,
            values_overlap_count=3,
            total_values=5,
        )
        assert abs(result - 0.720) < 0.001

    def test_zero_total_values_no_division_by_zero(self) -> None:
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=0.5,
            values_overlap_count=0,
            total_values=0,
        )
        assert 0.0 <= result <= 1.0

    def test_full_overlap_full_llm_returns_one(self) -> None:
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=1.0,
            values_overlap_count=10,
            total_values=10,
        )
        assert result == 1.0

    def test_negative_llm_alignment_clamped(self) -> None:
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=-1.0,
            values_overlap_count=0,
            total_values=1,
        )
        assert result == 0.0

    def test_overlap_exceeding_total_clamped(self) -> None:
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=0.0,
            values_overlap_count=20,
            total_values=5,
        )
        # overlap_ratio = 20/5 = 4.0 clamped to 1.0 → 0.40*1.0 = 0.4
        assert abs(result - 0.400) < 0.001

    def test_default_overlap_values(self) -> None:
        result = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
            llm_alignment=1.0,
        )
        # defaults: values_overlap_count=0, total_values=1 → ratio=0
        assert abs(result - 0.600) < 0.001


# ── validate_star_structure ────────────────────────────────────


class TestValidateStarStructure:
    def test_valid_star_returns_true(self) -> None:
        star = {
            "situation": "A production outage occurred",
            "task": "Identify and fix the root cause",
            "action": "Rolled back the bad deployment",
            "result": "System restored in 15 minutes",
        }
        assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is True

    def test_missing_situation_returns_false(self) -> None:
        star = {"task": "Fix it", "action": "Did it", "result": "Done"}
        assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False

    def test_empty_string_field_returns_false(self) -> None:
        star = {
            "situation": "Context",
            "task": "   ",  # whitespace only
            "action": "Something",
            "result": "Outcome",
        }
        assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False

    def test_none_field_returns_false(self) -> None:
        star = {
            "situation": "Context",
            "task": None,
            "action": "Something",
            "result": "Outcome",
        }
        assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False

    def test_non_string_field_returns_false(self) -> None:
        star = {
            "situation": "Context",
            "task": 123,
            "action": "Something",
            "result": "Outcome",
        }
        assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False

    def test_empty_dict_returns_false(self) -> None:
        assert InterviewIntelligenceAnalyzer.validate_star_structure({}) is False


# ── merge_salary_data ──────────────────────────────────────────


class TestMergeSalaryData:
    def test_empty_list_returns_no_data_message(self) -> None:
        result = InterviewIntelligenceAnalyzer.merge_salary_data(
            salary_estimates=[],
            target_role="Senior Engineer",
        )
        assert "No salary intelligence data" in result
        assert "Senior Engineer" in result

    def test_single_estimate_formatted_correctly(self) -> None:
        estimates = [
            {"median_salary": 80000, "range_min": 70000, "range_max": 90000, "data_source": "glassdoor"},
        ]
        result = InterviewIntelligenceAnalyzer.merge_salary_data(
            salary_estimates=estimates,
            target_role="Backend Dev",
            currency="EUR",
        )
        assert "Backend Dev" in result
        assert "80000" in result
        assert "70000-90000" in result
        assert "glassdoor" in result

    def test_only_first_5_estimates_used(self) -> None:
        estimates = [
            {"median_salary": i * 1000, "range_min": 0, "range_max": 0, "data_source": f"src{i}"}
            for i in range(10)
        ]
        result = InterviewIntelligenceAnalyzer.merge_salary_data(
            salary_estimates=estimates,
            target_role="Role",
        )
        assert "src4" in result
        assert "src5" not in result

    def test_missing_fields_show_na(self) -> None:
        estimates = [{}]
        result = InterviewIntelligenceAnalyzer.merge_salary_data(
            salary_estimates=estimates,
            target_role="Role",
        )
        assert "N/A" in result

    def test_currency_in_header(self) -> None:
        result = InterviewIntelligenceAnalyzer.merge_salary_data(
            salary_estimates=[{"median_salary": 1}],
            target_role="Dev",
            currency="USD",
        )
        assert "USD" in result


# ── _clamp_company_analysis ────────────────────────────────────


class TestClampCompanyAnalysis:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence_score": 2.0, "insights": []}
        _clamp_company_analysis(data)
        assert data["confidence_score"] == MAX_INTERVIEW_CONFIDENCE

    def test_confidence_negative_clamped_to_zero(self) -> None:
        data = {"confidence_score": -5.0, "insights": []}
        _clamp_company_analysis(data)
        assert data["confidence_score"] == 0.0

    def test_culture_alignment_capped_at_one(self) -> None:
        data = {"culture_alignment_score": 5.0, "insights": []}
        _clamp_company_analysis(data)
        assert data["culture_alignment_score"] == 1.0

    def test_invalid_insight_type_becomes_culture(self) -> None:
        data = {
            "insights": [{"insight_type": "unknown", "confidence": 0.5, "title": "Tip"}],
        }
        _clamp_company_analysis(data)
        assert data["insights"][0]["insight_type"] == "culture"

    def test_valid_insight_types_preserved(self) -> None:
        for itype in VALID_INSIGHT_TYPES:
            data = {"insights": [{"insight_type": itype, "confidence": 0.5, "title": "T"}]}
            _clamp_company_analysis(data)
            assert data["insights"][0]["insight_type"] == itype

    def test_insight_confidence_capped(self) -> None:
        data = {"insights": [{"insight_type": "culture", "confidence": 9.9, "title": "T"}]}
        _clamp_company_analysis(data)
        assert data["insights"][0]["confidence"] == MAX_INTERVIEW_CONFIDENCE

    def test_non_list_insights_becomes_empty_list(self) -> None:
        data = {"insights": "not a list"}
        _clamp_company_analysis(data)
        assert data["insights"] == []

    def test_missing_title_gets_default(self) -> None:
        data = {"insights": [{"insight_type": "culture", "confidence": 0.5}]}
        _clamp_company_analysis(data)
        assert data["insights"][0]["title"] == "Untitled insight"

    def test_missing_confidence_defaults_to_half(self) -> None:
        data = {"insights": [{"insight_type": "culture", "title": "T"}]}
        _clamp_company_analysis(data)
        # 0.5 is within bounds, should remain 0.5
        assert 0.0 <= data["insights"][0]["confidence"] <= MAX_INTERVIEW_CONFIDENCE


# ── _clamp_questions ───────────────────────────────────────────


class TestClampQuestions:
    def test_invalid_category_becomes_behavioral(self) -> None:
        questions = [{"category": "nonsense", "question_text": "Q?", "frequency_weight": 0.5}]
        _clamp_questions(questions)
        assert questions[0]["category"] == "behavioral"

    def test_valid_categories_preserved(self) -> None:
        for cat in VALID_QUESTION_CATEGORIES:
            q = [{"category": cat, "question_text": "Q?", "frequency_weight": 0.5}]
            _clamp_questions(q)
            assert q[0]["category"] == cat

    def test_missing_question_text_gets_default(self) -> None:
        questions = [{"category": "behavioral"}]
        _clamp_questions(questions)
        assert "No question generated" in questions[0]["question_text"]

    def test_frequency_weight_clamped_to_one(self) -> None:
        questions = [{"category": "behavioral", "question_text": "Q?", "frequency_weight": 9.0}]
        _clamp_questions(questions)
        assert questions[0]["frequency_weight"] == 1.0

    def test_frequency_weight_negative_clamped_to_zero(self) -> None:
        questions = [{"category": "behavioral", "question_text": "Q?", "frequency_weight": -3.0}]
        _clamp_questions(questions)
        assert questions[0]["frequency_weight"] == 0.0

    def test_invalid_difficulty_becomes_medium(self) -> None:
        questions = [{"category": "behavioral", "question_text": "Q?", "difficulty_level": "extreme"}]
        _clamp_questions(questions)
        assert questions[0]["difficulty_level"] == "medium"

    def test_valid_difficulty_levels_preserved(self) -> None:
        for level in VALID_DIFFICULTY_LEVELS:
            q = [{"category": "behavioral", "question_text": "Q?", "difficulty_level": level}]
            _clamp_questions(q)
            assert q[0]["difficulty_level"] == level

    def test_order_index_assigned_from_position(self) -> None:
        questions = [
            {"category": "behavioral", "question_text": "Q1?"},
            {"category": "technical", "question_text": "Q2?"},
        ]
        _clamp_questions(questions)
        assert questions[0]["order_index"] == 0
        assert questions[1]["order_index"] == 1

    def test_existing_order_index_preserved(self) -> None:
        questions = [{"category": "behavioral", "question_text": "Q?", "order_index": 42}]
        _clamp_questions(questions)
        assert questions[0]["order_index"] == 42


# ── _clamp_star_examples ───────────────────────────────────────


class TestClampStarExamples:
    def test_missing_star_fields_get_placeholders(self) -> None:
        examples = [{}]
        _clamp_star_examples(examples)
        for field in ("situation", "task", "action", "result"):
            assert field.title() in examples[0][field] or field in examples[0][field]

    def test_relevance_score_clamped_to_one(self) -> None:
        examples = [
            {"situation": "S", "task": "T", "action": "A", "result": "R", "relevance_score": 5.0},
        ]
        _clamp_star_examples(examples)
        assert examples[0]["relevance_score"] == 1.0

    def test_relevance_score_negative_clamped_to_zero(self) -> None:
        examples = [
            {"situation": "S", "task": "T", "action": "A", "result": "R", "relevance_score": -1.0},
        ]
        _clamp_star_examples(examples)
        assert examples[0]["relevance_score"] == 0.0

    def test_order_index_assigned_from_position(self) -> None:
        examples = [
            {"situation": "S", "task": "T", "action": "A", "result": "R"},
            {"situation": "S", "task": "T", "action": "A", "result": "R"},
        ]
        _clamp_star_examples(examples)
        assert examples[0]["order_index"] == 0
        assert examples[1]["order_index"] == 1

    def test_existing_fields_not_overwritten_if_present(self) -> None:
        examples = [
            {"situation": "Real situation", "task": "Real task", "action": "Real action", "result": "Real result"},
        ]
        _clamp_star_examples(examples)
        assert examples[0]["situation"] == "Real situation"


# ── _clamp_negotiation_script ──────────────────────────────────


class TestClampNegotiationScript:
    def test_missing_scripts_get_defaults(self) -> None:
        data: dict = {}
        _clamp_negotiation_script(data)
        for field in ("opening_script", "counteroffer_script", "fallback_script"):
            assert len(data[field]) > 0

    def test_existing_scripts_preserved(self) -> None:
        data = {
            "opening_script": "My opening",
            "counteroffer_script": "My counter",
            "fallback_script": "My fallback",
        }
        _clamp_negotiation_script(data)
        assert data["opening_script"] == "My opening"

    def test_non_list_key_arguments_becomes_empty_list(self) -> None:
        data = {"key_arguments": "not a list"}
        _clamp_negotiation_script(data)
        assert data["key_arguments"] == []

    def test_list_key_arguments_preserved(self) -> None:
        data = {"key_arguments": ["arg1", "arg2"]}
        _clamp_negotiation_script(data)
        assert data["key_arguments"] == ["arg1", "arg2"]

    def test_non_dict_skill_premiums_becomes_empty_dict(self) -> None:
        data = {"skill_premiums": ["Python"]}
        _clamp_negotiation_script(data)
        assert data["skill_premiums"] == {}

    def test_salary_fields_clamped_non_negative(self) -> None:
        data = {
            "salary_range_min": -1000.0,
            "salary_range_max": 90000.0,
            "salary_range_median": -500.0,
        }
        _clamp_negotiation_script(data)
        assert data["salary_range_min"] == 0.0
        assert data["salary_range_max"] == 90000.0
        assert data["salary_range_median"] == 0.0

    def test_invalid_salary_value_becomes_none(self) -> None:
        data = {"salary_range_min": "not-a-number"}
        _clamp_negotiation_script(data)
        assert data["salary_range_min"] is None

    def test_none_salary_stays_none(self) -> None:
        data = {"salary_range_min": None}
        _clamp_negotiation_script(data)
        assert data["salary_range_min"] is None


# ── analyze_company (LLM) ──────────────────────────────────────


class TestAnalyzeCompany:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        llm_response = {"confidence_score": 0.7, "culture_alignment_score": 0.8, "insights": []}
        with _patch_sanitize(), _patch_complete_json(llm_response):
            result = await InterviewIntelligenceAnalyzer.analyze_company(
                company_name="TechCorp",
                target_role="Senior Engineer",
                prep_depth="standard",
                current_role="Engineer",
                current_seniority="mid",
                current_industry="Technology",
                skills="Python, FastAPI",
                years_experience=5,
            )
        assert isinstance(result, dict)
        assert result["confidence_score"] <= MAX_INTERVIEW_CONFIDENCE

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.interview_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await InterviewIntelligenceAnalyzer.analyze_company(
                company_name="Corp",
                target_role="Dev",
                prep_depth="quick",
                current_role="Dev",
                current_seniority="junior",
                current_industry="Tech",
                skills="Python",
                years_experience=2,
            )
        assert result == {}

    @pytest.mark.asyncio
    async def test_confidence_clamped_in_output(self) -> None:
        llm_response = {"confidence_score": 99.9, "insights": []}
        with _patch_sanitize(), _patch_complete_json(llm_response):
            result = await InterviewIntelligenceAnalyzer.analyze_company(
                company_name="Corp",
                target_role="Dev",
                prep_depth="quick",
                current_role="Dev",
                current_seniority="senior",
                current_industry="Tech",
                skills="Python",
                years_experience=10,
            )
        assert result["confidence_score"] == MAX_INTERVIEW_CONFIDENCE

    @pytest.mark.asyncio
    async def test_company_name_passed_to_prompt(self) -> None:
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {"insights": []}

        with _patch_sanitize(), patch("app.ai.interview_intelligence_analyzer.complete_json", side_effect=_capture):
            await InterviewIntelligenceAnalyzer.analyze_company(
                company_name="UniqueCompanyXYZ",
                target_role="Dev",
                prep_depth="quick",
                current_role="Dev",
                current_seniority="mid",
                current_industry="Tech",
                skills="Python",
                years_experience=5,
            )

        assert "UniqueCompanyXYZ" in captured[0]


# ── generate_questions (LLM) ──────────────────────────────────


class TestGenerateQuestions:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        questions = [{"category": "behavioral", "question_text": "Tell me about yourself."}]
        with _patch_sanitize(), _patch_complete_json(questions):
            result = await InterviewIntelligenceAnalyzer.generate_questions(
                company_name="Corp",
                target_role="Dev",
                interview_format="structured",
                company_brief="Brief",
                current_role="Dev",
                skills="Python",
                years_experience=5,
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dict_response_extracts_questions_key(self) -> None:
        questions = [{"category": "technical", "question_text": "Explain OOP."}]
        with _patch_sanitize(), _patch_complete_json({"questions": questions, "other": "data"}):
            result = await InterviewIntelligenceAnalyzer.generate_questions(
                company_name="Corp",
                target_role="Dev",
                interview_format="panel",
                company_brief="Brief",
                current_role="Dev",
                skills="Python",
                years_experience=5,
            )
        assert len(result) == 1
        assert result[0]["category"] == "technical"

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.interview_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await InterviewIntelligenceAnalyzer.generate_questions(
                company_name="Corp",
                target_role="Dev",
                interview_format="one-on-one",
                company_brief="Brief",
                current_role="Dev",
                skills="Python",
                years_experience=5,
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_category_clamped(self) -> None:
        questions = [{"category": "invalid_cat", "question_text": "Q?", "frequency_weight": 0.5}]
        with _patch_sanitize(), _patch_complete_json(questions):
            result = await InterviewIntelligenceAnalyzer.generate_questions(
                company_name="Corp",
                target_role="Dev",
                interview_format="one-on-one",
                company_brief="Brief",
                current_role="Dev",
                skills="Python",
                years_experience=5,
            )
        assert result[0]["category"] == "behavioral"


# ── generate_star_examples (LLM) ──────────────────────────────


class TestGenerateStarExamples:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        examples = [
            {"situation": "S", "task": "T", "action": "A", "result": "R", "relevance_score": 0.9},
        ]
        with _patch_sanitize(), _patch_complete_json(examples):
            result = await InterviewIntelligenceAnalyzer.generate_star_examples(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                career_summary="Summary",
                skills="Python",
                experience_blueprint="Blueprint",
                growth_trajectory="Upward",
                values_profile="Values",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dict_response_extracts_star_examples_key(self) -> None:
        examples = [{"situation": "S", "task": "T", "action": "A", "result": "R"}]
        with _patch_sanitize(), _patch_complete_json({"star_examples": examples}):
            result = await InterviewIntelligenceAnalyzer.generate_star_examples(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                career_summary="Summary",
                skills="Python",
                experience_blueprint="Blueprint",
                growth_trajectory="Upward",
                values_profile="Values",
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.interview_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await InterviewIntelligenceAnalyzer.generate_star_examples(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                career_summary="Summary",
                skills="Python",
                experience_blueprint="Blueprint",
                growth_trajectory="Upward",
                values_profile="Values",
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_star_fields_filled(self) -> None:
        examples = [{}]
        with _patch_sanitize(), _patch_complete_json(examples):
            result = await InterviewIntelligenceAnalyzer.generate_star_examples(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                career_summary="Summary",
                skills="Python",
                experience_blueprint="Blueprint",
                growth_trajectory="Upward",
                values_profile="Values",
            )
        for field in ("situation", "task", "action", "result"):
            assert result[0][field]  # non-empty


# ── generate_negotiation_script (LLM) ─────────────────────────


class TestGenerateNegotiationScript:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "opening_script": "I'd like to discuss salary.",
            "counteroffer_script": "Based on market data...",
            "fallback_script": "I understand your constraints.",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await InterviewIntelligenceAnalyzer.generate_negotiation_script(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                current_seniority="senior",
                skills="Python",
                years_experience=8,
                salary_data="Median: 90000",
                target_salary=95000.0,
                currency="EUR",
            )
        assert isinstance(result, dict)
        assert "opening_script" in result

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.interview_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await InterviewIntelligenceAnalyzer.generate_negotiation_script(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                current_seniority="mid",
                skills="Python",
                years_experience=5,
                salary_data="No data",
            )
        assert result == {}

    @pytest.mark.asyncio
    async def test_none_target_salary_uses_not_specified(self) -> None:
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {}

        with _patch_sanitize(), patch("app.ai.interview_intelligence_analyzer.complete_json", side_effect=_capture):
            await InterviewIntelligenceAnalyzer.generate_negotiation_script(
                company_name="Corp",
                target_role="Dev",
                current_role="Dev",
                current_seniority="mid",
                skills="Python",
                years_experience=5,
                salary_data="Data",
                target_salary=None,
            )

        assert "Not specified" in captured[0]


# ── compare_preps (LLM) ───────────────────────────────────────


class TestComparePreps:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {"ranked_preps": [{"id": "prep1", "rank": 1}]}
        with _patch_sanitize(), _patch_complete_json(response):
            result = await InterviewIntelligenceAnalyzer.compare_preps(
                current_role="Dev",
                current_seniority="senior",
                current_industry="Tech",
                preps_json='[{"id": "prep1"}]',
            )
        assert isinstance(result, dict)
        assert "ranked_preps" in result

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.interview_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await InterviewIntelligenceAnalyzer.compare_preps(
                current_role="Dev",
                current_seniority="mid",
                current_industry="Tech",
                preps_json="[]",
            )
        assert result == {}

    @pytest.mark.asyncio
    async def test_role_passed_to_prompt(self) -> None:
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {}

        with _patch_sanitize(), patch("app.ai.interview_intelligence_analyzer.complete_json", side_effect=_capture):
            await InterviewIntelligenceAnalyzer.compare_preps(
                current_role="DataScientistXYZ",
                current_seniority="principal",
                current_industry="Finance",
                preps_json="[]",
            )

        assert "DataScientistXYZ" in captured[0]
