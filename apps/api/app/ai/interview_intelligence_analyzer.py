"""
PathForge AI Engine — Interview Intelligence Analyzer
=======================================================
AI pipeline for the Interview Intelligence Engine™ — the industry's
first system combining company-specific preparation, Career DNA–powered
STAR examples, and data-backed salary negotiation.

4 LLM methods:
    1. analyze_company — Company intelligence extraction
    2. generate_questions — Company+role-specific question prediction
    3. generate_star_examples — Career DNA–mapped STAR responses
    4. generate_negotiation_script — Data-backed salary scripts

5 Static helpers:
    1. compute_interview_confidence — Composite capped at 0.85
    2. calculate_culture_alignment — CareerDNA ↔ company alignment
    3. validate_star_structure — Ensure all STAR components present
    4. merge_salary_data — Integrate Salary Intelligence data
    5. compare_preps — Multi-prep ranking

3 Clamping validators:
    1. _clamp_company_analysis — Cap confidence, validate insights
    2. _clamp_questions — Validate categories, cap frequency
    3. _clamp_star_examples — Validate STAR structure, cap relevance

All methods follow the established PathForge analyzer pattern:
    - Static async methods for LLM calls
    - complete_json for structured LLM output
    - sanitize_user_text before all LLM calls
    - Timing + structured logging
    - Safe fallbacks on error
"""

import logging
import time
from typing import Any

from app.ai.interview_intelligence_prompts import (
    COMPANY_ANALYSIS_PROMPT,
    NEGOTIATION_SCRIPT_PROMPT,
    PREP_COMPARISON_PROMPT,
    PROMPT_VERSION,
    QUESTION_GENERATION_PROMPT,
    STAR_EXAMPLE_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

MAX_INTERVIEW_CONFIDENCE = 0.85
"""Hard ceiling for LLM-generated interview confidence scores."""

VALID_INSIGHT_TYPES = {"format", "culture", "salary_band", "process", "values"}
"""Valid insight type values for company insights."""

VALID_QUESTION_CATEGORIES = {"behavioral", "technical", "situational", "culture_fit", "salary"}
"""Valid question category values."""

VALID_DIFFICULTY_LEVELS = {"easy", "medium", "hard"}
"""Valid difficulty level values for questions."""


class InterviewIntelligenceAnalyzer:
    """
    AI pipeline for Interview Intelligence™ analysis.

    Each method performs a focused LLM call and returns
    validated structured data. All interview intelligence
    includes transparent source attribution.
    """

    # ── Static Helpers ─────────────────────────────────────────

    @staticmethod
    def compute_interview_confidence(
        *,
        llm_confidence: float,
        data_quality_factor: float = 0.5,
        career_dna_completeness: float = 0.5,
    ) -> float:
        """
        Compute composite interview prep confidence, capped at 0.85.

        Formula:
            weighted = 0.40 × llm
                     + 0.30 × career_dna_completeness
                     + 0.30 × data_quality
            clamped to [0.0, MAX_INTERVIEW_CONFIDENCE]

        Args:
            llm_confidence: Raw LLM confidence (0-1).
            data_quality_factor: Available data quality (0-1).
            career_dna_completeness: Career DNA completeness (0-1).

        Returns:
            Capped confidence from 0.0 to 0.85.
        """
        llm_factor = max(0.0, min(MAX_INTERVIEW_CONFIDENCE, llm_confidence))
        dna_factor = max(0.0, min(1.0, career_dna_completeness))
        data_factor = max(0.0, min(1.0, data_quality_factor))

        weighted = (
            0.40 * llm_factor
            + 0.30 * dna_factor
            + 0.30 * data_factor
        )

        return float(
            max(0.0, min(MAX_INTERVIEW_CONFIDENCE, round(weighted, 3)))
        )

    @staticmethod
    def calculate_culture_alignment(
        *,
        llm_alignment: float,
        values_overlap_count: int = 0,
        total_values: int = 1,
    ) -> float:
        """
        Calculate culture alignment between CareerDNA and company.

        Combines LLM-assessed alignment with values overlap ratio.

        Args:
            llm_alignment: LLM-assessed alignment score (0-1).
            values_overlap_count: Number of matching values.
            total_values: Total values considered.

        Returns:
            Culture alignment score from 0.0 to 1.0.
        """
        llm_score = max(0.0, min(1.0, llm_alignment))
        overlap_ratio = (
            values_overlap_count / max(total_values, 1)
        )
        overlap_score = max(0.0, min(1.0, overlap_ratio))

        combined = 0.60 * llm_score + 0.40 * overlap_score
        return float(max(0.0, min(1.0, round(combined, 3))))

    @staticmethod
    def validate_star_structure(star: dict[str, Any]) -> bool:
        """
        Validate that a STAR example has all required components.

        Args:
            star: Dictionary with situation, task, action, result.

        Returns:
            True if all STAR components are non-empty strings.
        """
        required_fields = ("situation", "task", "action", "result")
        return all(
            isinstance(star.get(field), str) and len(star.get(field, "").strip()) > 0
            for field in required_fields
        )

    @staticmethod
    def merge_salary_data(
        *,
        salary_estimates: list[dict[str, Any]],
        target_role: str,
        currency: str = "EUR",
    ) -> str:
        """
        Format salary intelligence data for LLM consumption.

        Args:
            salary_estimates: List of salary estimate dicts.
            target_role: Target role for context.
            currency: Currency code.

        Returns:
            Formatted salary data string for prompt injection.
        """
        if not salary_estimates:
            return f"No salary intelligence data available for {target_role}."

        lines = [f"Salary data for {target_role} ({currency}):"]
        for estimate in salary_estimates[:5]:
            median = estimate.get("median_salary", "N/A")
            range_min = estimate.get("range_min", "N/A")
            range_max = estimate.get("range_max", "N/A")
            source = estimate.get("data_source", "unknown")
            lines.append(
                f"  - Median: {median}, Range: {range_min}-{range_max} "
                f"(source: {source})"
            )
        return "\n".join(lines)

    # ── LLM: Company Analysis ─────────────────────────────────

    @staticmethod
    async def analyze_company(
        *,
        company_name: str,
        target_role: str,
        prep_depth: str,
        current_role: str,
        current_seniority: str,
        current_industry: str,
        skills: str,
        years_experience: int,
    ) -> dict[str, Any]:
        """
        Analyze a company and role for interview intelligence.

        Produces company brief, interview format, culture alignment,
        and structured insights.

        Args:
            company_name: Target company name.
            target_role: Target role at the company.
            prep_depth: Preparation depth (quick/standard/comprehensive).
            current_role: User's current role title.
            current_seniority: User's current seniority level.
            current_industry: User's current industry.
            skills: Formatted current skills string.
            years_experience: Total professional years.

        Returns:
            Dict with analysis details or empty dict on error.
        """
        clean_company, _ = sanitize_user_text(
            company_name, max_length=255, context="interview_company",
        )
        clean_role, _ = sanitize_user_text(
            target_role, max_length=255, context="interview_role",
        )
        clean_current_role, _ = sanitize_user_text(
            current_role, max_length=255, context="interview_current_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority, max_length=100, context="interview_seniority",
        )
        clean_industry, _ = sanitize_user_text(
            current_industry, max_length=255, context="interview_industry",
        )
        clean_skills, _ = sanitize_user_text(
            skills, max_length=3000, context="interview_skills",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=COMPANY_ANALYSIS_PROMPT.format(
                    version=PROMPT_VERSION,
                    company_name=clean_company,
                    target_role=clean_role,
                    prep_depth=prep_depth,
                    current_role=clean_current_role,
                    current_seniority=clean_seniority,
                    current_industry=clean_industry,
                    skills=clean_skills,
                    years_experience=years_experience,
                ),
                system_prompt="You are the PathForge Interview Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=4096,
            )

            _clamp_company_analysis(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Company analyzed: %s for %s — "
                "confidence=%.2f, alignment=%.2f (%.2fs)",
                clean_company,
                clean_role,
                data.get("confidence_score", 0),
                data.get("culture_alignment_score", 0),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Company analysis failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: Question Generation ───────────────────────────────

    @staticmethod
    async def generate_questions(
        *,
        company_name: str,
        target_role: str,
        interview_format: str,
        company_brief: str,
        current_role: str,
        skills: str,
        years_experience: int,
        category_filter: str | None = None,
        max_questions: int = 15,
    ) -> list[dict[str, Any]]:
        """
        Generate company+role-specific interview questions.

        Produces categorized questions with suggested answers
        and frequency weights.

        Args:
            company_name: Target company name.
            target_role: Target role at the company.
            interview_format: Detected interview format.
            company_brief: Company overview.
            current_role: User's current role.
            skills: User's key skills.
            years_experience: Professional experience years.
            category_filter: Optional category filter.
            max_questions: Maximum questions to generate.

        Returns:
            List of question dicts or empty list on error.
        """
        clean_company, _ = sanitize_user_text(
            company_name, max_length=255, context="question_company",
        )
        clean_role, _ = sanitize_user_text(
            target_role, max_length=255, context="question_role",
        )
        clean_format, _ = sanitize_user_text(
            interview_format or "Unknown format",
            max_length=500, context="question_format",
        )
        clean_brief, _ = sanitize_user_text(
            company_brief or "No brief available",
            max_length=1000, context="question_brief",
        )
        clean_current_role, _ = sanitize_user_text(
            current_role, max_length=255, context="question_current_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills, max_length=3000, context="question_skills",
        )

        filter_instruction = category_filter or "all categories"

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=QUESTION_GENERATION_PROMPT.format(
                    version=PROMPT_VERSION,
                    company_name=clean_company,
                    target_role=clean_role,
                    interview_format=clean_format,
                    company_brief=clean_brief,
                    current_role=clean_current_role,
                    skills=clean_skills,
                    years_experience=years_experience,
                    category_filter=filter_instruction,
                    max_questions=max_questions,
                ),
                system_prompt="You are the PathForge Interview Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.2,
                max_tokens=4096,
            )

            questions: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("questions", [])
            )

            _clamp_questions(questions)

            elapsed = time.monotonic() - start
            logger.info(
                "Questions generated: %d items for %s at %s (%.2fs)",
                len(questions),
                clean_role,
                clean_company,
                elapsed,
            )
            return questions

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Question generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: STAR Example Generation ───────────────────────────

    @staticmethod
    async def generate_star_examples(
        *,
        company_name: str,
        target_role: str,
        current_role: str,
        career_summary: str,
        skills: str,
        experience_blueprint: str,
        growth_trajectory: str,
        values_profile: str,
        question_context: str = "No specific questions provided.",
        max_examples: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Generate Career DNA–mapped STAR examples.

        Uses the user's actual experience and Career DNA to create
        personalized STAR responses for likely interview questions.

        Args:
            company_name: Target company name.
            target_role: Target role at the company.
            current_role: User's current role.
            career_summary: Career DNA summary.
            skills: Key skills from Career DNA.
            experience_blueprint: Career experience pattern.
            growth_trajectory: Career growth trajectory.
            values_profile: Career values profile.
            question_context: Optional questions to map STARs to.
            max_examples: Maximum STAR examples to generate.

        Returns:
            List of STAR example dicts or empty list on error.
        """
        clean_company, _ = sanitize_user_text(
            company_name, max_length=255, context="star_company",
        )
        clean_role, _ = sanitize_user_text(
            target_role, max_length=255, context="star_role",
        )
        clean_current_role, _ = sanitize_user_text(
            current_role, max_length=255, context="star_current_role",
        )
        clean_summary, _ = sanitize_user_text(
            career_summary or "No career summary available",
            max_length=3000, context="star_summary",
        )
        clean_skills, _ = sanitize_user_text(
            skills, max_length=3000, context="star_skills",
        )
        clean_experience, _ = sanitize_user_text(
            experience_blueprint or "No experience data",
            max_length=2000, context="star_experience",
        )
        clean_growth, _ = sanitize_user_text(
            growth_trajectory or "No growth data",
            max_length=2000, context="star_growth",
        )
        clean_values, _ = sanitize_user_text(
            values_profile or "No values data",
            max_length=2000, context="star_values",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=STAR_EXAMPLE_PROMPT.format(
                    version=PROMPT_VERSION,
                    company_name=clean_company,
                    target_role=clean_role,
                    current_role=clean_current_role,
                    career_summary=clean_summary,
                    skills=clean_skills,
                    experience_blueprint=clean_experience,
                    growth_trajectory=clean_growth,
                    values_profile=clean_values,
                    question_context=question_context,
                    max_examples=max_examples,
                ),
                system_prompt="You are the PathForge Interview Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=4096,
            )

            examples: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("star_examples", [])
            )

            _clamp_star_examples(examples)

            elapsed = time.monotonic() - start
            logger.info(
                "STAR examples generated: %d items (%.2fs)",
                len(examples),
                elapsed,
            )
            return examples

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "STAR example generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Negotiation Script Generation ─────────────────────

    @staticmethod
    async def generate_negotiation_script(
        *,
        company_name: str,
        target_role: str,
        current_role: str,
        current_seniority: str,
        skills: str,
        years_experience: int,
        salary_data: str,
        target_salary: float | None = None,
        currency: str = "EUR",
    ) -> dict[str, Any]:
        """
        Generate data-backed salary negotiation scripts.

        Uses Salary Intelligence Engine™ data to produce
        professional negotiation strategies.

        Args:
            company_name: Target company name.
            target_role: Target role at the company.
            current_role: User's current role.
            current_seniority: User's current seniority.
            skills: Key skills string.
            years_experience: Professional years.
            salary_data: Formatted salary intelligence data.
            target_salary: Optional target salary anchor.
            currency: Currency code.

        Returns:
            Dict with negotiation scripts or empty dict on error.
        """
        clean_company, _ = sanitize_user_text(
            company_name, max_length=255, context="negotiation_company",
        )
        clean_role, _ = sanitize_user_text(
            target_role, max_length=255, context="negotiation_role",
        )
        clean_current_role, _ = sanitize_user_text(
            current_role, max_length=255, context="negotiation_current_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority, max_length=100, context="negotiation_seniority",
        )
        clean_skills, _ = sanitize_user_text(
            skills, max_length=3000, context="negotiation_skills",
        )

        target_salary_str = str(target_salary) if target_salary else "Not specified"

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=NEGOTIATION_SCRIPT_PROMPT.format(
                    version=PROMPT_VERSION,
                    company_name=clean_company,
                    target_role=clean_role,
                    current_role=clean_current_role,
                    current_seniority=clean_seniority,
                    skills=clean_skills,
                    years_experience=years_experience,
                    salary_data=salary_data,
                    target_salary=target_salary_str,
                    currency=currency,
                ),
                system_prompt="You are the PathForge Interview Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.2,
                max_tokens=4096,
            )

            _clamp_negotiation_script(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Negotiation script generated for %s at %s (%.2fs)",
                clean_role,
                clean_company,
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Negotiation script generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: Prep Comparison ───────────────────────────────────

    @staticmethod
    async def compare_preps(
        *,
        current_role: str,
        current_seniority: str,
        current_industry: str,
        preps_json: str,
    ) -> dict[str, Any]:
        """
        Compare multiple interview preps and provide ranked analysis.

        Args:
            current_role: User's current role.
            current_seniority: User's current seniority.
            current_industry: User's current industry.
            preps_json: JSON string of preps to compare.

        Returns:
            Dict with ranking and analysis or empty dict on error.
        """
        clean_role, _ = sanitize_user_text(
            current_role, max_length=255, context="compare_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority, max_length=100, context="compare_seniority",
        )
        clean_industry, _ = sanitize_user_text(
            current_industry, max_length=255, context="compare_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=PREP_COMPARISON_PROMPT.format(
                    version=PROMPT_VERSION,
                    current_role=clean_role,
                    current_seniority=clean_seniority,
                    current_industry=clean_industry,
                    preps_json=preps_json,
                ),
                system_prompt="You are the PathForge Interview Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            elapsed = time.monotonic() - start
            logger.info(
                "Prep comparison completed (%.2fs)",
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Prep comparison failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}


# ── Private Validation Helpers ─────────────────────────────────


def _clamp_company_analysis(data: dict[str, Any]) -> None:
    """Validate and clamp company analysis fields in-place."""
    # Cap confidence at MAX
    confidence = data.get("confidence_score", 0.5)
    data["confidence_score"] = max(
        0.0, min(MAX_INTERVIEW_CONFIDENCE, float(confidence))
    )

    # Cap culture alignment at 1.0
    alignment = data.get("culture_alignment_score", 0.5)
    data["culture_alignment_score"] = max(0.0, min(1.0, float(alignment)))

    # Ensure insights is a list
    insights = data.get("insights", [])
    if not isinstance(insights, list):
        data["insights"] = []
    else:
        for insight in insights:
            # Validate insight type
            if insight.get("insight_type", "") not in VALID_INSIGHT_TYPES:
                insight["insight_type"] = "culture"
            # Cap insight confidence
            conf = insight.get("confidence", 0.5)
            insight["confidence"] = max(
                0.0, min(MAX_INTERVIEW_CONFIDENCE, float(conf))
            )
            # Ensure title
            if not insight.get("title"):
                insight["title"] = "Untitled insight"


def _clamp_questions(questions: list[dict[str, Any]]) -> None:
    """Validate and clamp question fields in-place."""
    for index, question in enumerate(questions):
        # Validate category
        if question.get("category", "") not in VALID_QUESTION_CATEGORIES:
            question["category"] = "behavioral"

        # Ensure question text
        if not question.get("question_text"):
            question["question_text"] = "No question generated"

        # Clamp frequency weight
        freq = question.get("frequency_weight", 0.5)
        question["frequency_weight"] = max(0.0, min(1.0, float(freq)))

        # Validate difficulty
        if question.get("difficulty_level", "") not in VALID_DIFFICULTY_LEVELS:
            question["difficulty_level"] = "medium"

        # Ensure order index
        question["order_index"] = question.get("order_index", index)


def _clamp_star_examples(examples: list[dict[str, Any]]) -> None:
    """Validate and clamp STAR example fields in-place."""
    for index, example in enumerate(examples):
        # Ensure all STAR components exist
        for field in ("situation", "task", "action", "result"):
            if not example.get(field):
                example[field] = f"[{field.title()} not generated]"

        # Clamp relevance score
        relevance = example.get("relevance_score", 0.5)
        example["relevance_score"] = max(0.0, min(1.0, float(relevance)))

        # Ensure order index
        example["order_index"] = example.get("order_index", index)


def _clamp_negotiation_script(data: dict[str, Any]) -> None:
    """Validate and clamp negotiation script fields in-place."""
    # Ensure all script fields exist
    for field in ("opening_script", "counteroffer_script", "fallback_script"):
        if not data.get(field):
            data[field] = f"[{field.replace('_', ' ').title()} not generated]"

    # Ensure key arguments is a list
    if not isinstance(data.get("key_arguments"), list):
        data["key_arguments"] = []

    # Ensure skill premiums is a dict
    if not isinstance(data.get("skill_premiums"), dict):
        data["skill_premiums"] = {}

    # Clamp salary values
    for field in ("salary_range_min", "salary_range_max", "salary_range_median"):
        value = data.get(field)
        if value is not None:
            try:
                data[field] = max(0.0, float(value))
            except (ValueError, TypeError):
                data[field] = None
