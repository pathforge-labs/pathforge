"""
PathForge — Cross-Border Career Passport™ AI Analyzer
=======================================================
LLM-powered career mobility analysis pipeline for credential mapping,
country comparison, visa assessment, and market demand analysis.

LLM Methods (4):
    analyze_credential_mapping   — Map qualification via EQF
    analyze_country_comparison   — Side-by-side country analysis
    analyze_visa_feasibility     — Visa eligibility assessment
    analyze_market_demand        — Role demand by country

Static Methods (4):
    compute_passport_score       — Composite readiness metric
    compute_credential_confidence — Credential mapping confidence
    compute_financial_score      — Financial attractiveness score
    compute_demand_score         — Market demand score

Clamping Validators (4, module-level):
    _clamp_credential_mapping    — Validate and clamp credential data
    _clamp_country_comparison    — Validate and clamp comparison data
    _clamp_visa_assessment       — Validate and clamp visa data
    _clamp_market_demand         — Validate and clamp demand data
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.career_passport_prompts import (
    COUNTRY_COMPARISON_PROMPT,
    CREDENTIAL_MAPPING_PROMPT,
    MARKET_DEMAND_PROMPT,
    VISA_ASSESSMENT_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

MAX_PASSPORT_CONFIDENCE = 0.85

VALID_EQF_LEVELS = frozenset({
    "level_1", "level_2", "level_3", "level_4",
    "level_5", "level_6", "level_7", "level_8",
})

VALID_DEMAND_LEVELS = frozenset({
    "low", "moderate", "high", "very_high",
})

VALID_VISA_CATEGORIES = frozenset({
    "free_movement", "work_permit", "blue_card",
    "skilled_worker", "investor", "other",
})


class CareerPassportAnalyzer:
    """AI pipeline for Cross-Border Career Passport™ mobility analysis."""

    # ── LLM Methods ────────────────────────────────────────────

    @staticmethod
    async def analyze_credential_mapping(
        *,
        source_qualification: str,
        source_country: str,
        target_country: str,
        primary_role: str,
        primary_industry: str,
        years_experience: int,
    ) -> dict[str, Any]:
        """Map a qualification to its EQF equivalent.

        EQF Intelligence Engine™ — uses AI to determine the closest
        equivalent qualification in the target country's framework.

        Args:
            source_qualification: Qualification/degree to map.
            source_country: Country where obtained.
            target_country: Target country for mapping.
            primary_role: User's primary role.
            primary_industry: User's industry.
            years_experience: User's experience.

        Returns:
            Dict with equivalent_level, eqf_level, confidence, etc.
        """
        clean_qual, _ = sanitize_user_text(
            source_qualification, max_length=500, context="credential_qual",
        )
        clean_source, _ = sanitize_user_text(
            source_country, max_length=100, context="credential_source",
        )
        clean_target, _ = sanitize_user_text(
            target_country, max_length=100, context="credential_target",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="credential_role",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=CREDENTIAL_MAPPING_PROMPT.format(
                    source_qualification=clean_qual,
                    source_country=clean_source,
                    target_country=clean_target,
                    primary_role=clean_role,
                    primary_industry=primary_industry or "Technology",
                    years_experience=years_experience,
                ),
                system_prompt="You are the PathForge EQF Intelligence Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=512,
            )

            _clamp_credential_mapping(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Credential mapping %s → %s completed — "
                "EQF %s, confidence %.2f (%.2fs)",
                clean_source, clean_target,
                result.get("eqf_level", "unknown"),
                result.get("confidence", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Credential mapping failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "equivalent_level": "Assessment unavailable",
                "eqf_level": "level_6",
                "recognition_notes": "AI analysis failed — use ENIC-NARIC.",
                "framework_reference": None,
                "confidence": 0.0,
            }

    @staticmethod
    async def analyze_country_comparison(
        *,
        source_country: str,
        target_country: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        years_experience: int,
        salary_context: str,
    ) -> dict[str, Any]:
        """Compare two countries for career mobility.

        Purchasing Power Calculator™ — analyzes cost of living,
        salary delta, tax impact, and market demand for the user's
        specific role and seniority.

        Args:
            source_country: Current country.
            target_country: Target country.
            primary_role: User's role.
            seniority_level: User's seniority.
            primary_industry: User's industry.
            years_experience: User's experience.
            salary_context: Current salary context.

        Returns:
            Dict with col_delta_pct, salary_delta_pct, etc.
        """
        clean_source, _ = sanitize_user_text(
            source_country, max_length=100, context="compare_source",
        )
        clean_target, _ = sanitize_user_text(
            target_country, max_length=100, context="compare_target",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="compare_role",
        )
        clean_salary, _ = sanitize_user_text(
            salary_context or "Not provided", max_length=500,
            context="compare_salary",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=COUNTRY_COMPARISON_PROMPT.format(
                    source_country=clean_source,
                    target_country=clean_target,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    years_experience=years_experience,
                    salary_context=clean_salary,
                ),
                system_prompt="You are the PathForge Purchasing Power Calculator.",
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=768,
            )

            _clamp_country_comparison(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Country comparison %s → %s completed — "
                "PP delta %.1f%% (%.2fs)",
                clean_source, clean_target,
                result.get("purchasing_power_delta", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Country comparison failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "col_delta_pct": 0.0,
                "salary_delta_pct": 0.0,
                "purchasing_power_delta": 0.0,
                "tax_impact_notes": "Analysis unavailable.",
                "market_demand_level": "moderate",
                "detailed_breakdown": None,
            }

    @staticmethod
    async def analyze_visa_feasibility(
        *,
        nationality: str,
        target_country: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        years_experience: int,
        education_level: str,
    ) -> dict[str, Any]:
        """Assess visa/work permit feasibility.

        Visa Eligibility Predictor™ — determines the most likely
        visa category, eligibility score, requirements, and timeline.

        Args:
            nationality: User's nationality.
            target_country: Target country.
            primary_role: User's role.
            seniority_level: User's seniority.
            primary_industry: User's industry.
            years_experience: User's experience.
            education_level: User's education level.

        Returns:
            Dict with visa_type, eligibility_score, requirements, etc.
        """
        clean_nationality, _ = sanitize_user_text(
            nationality, max_length=100, context="visa_nationality",
        )
        clean_target, _ = sanitize_user_text(
            target_country, max_length=100, context="visa_target",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="visa_role",
        )
        clean_education, _ = sanitize_user_text(
            education_level or "bachelor", max_length=100,
            context="visa_education",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=VISA_ASSESSMENT_PROMPT.format(
                    nationality=clean_nationality,
                    target_country=clean_target,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    years_experience=years_experience,
                    education_level=clean_education,
                ),
                system_prompt="You are the PathForge Visa Eligibility Predictor.",
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=768,
            )

            _clamp_visa_assessment(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Visa assessment for %s → %s completed — "
                "type %s, score %.2f (%.2fs)",
                clean_nationality, clean_target,
                result.get("visa_type", "unknown"),
                result.get("eligibility_score", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Visa assessment failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "visa_type": "other",
                "eligibility_score": 0.0,
                "requirements": None,
                "processing_time_weeks": None,
                "estimated_cost": None,
                "notes": "Analysis unavailable — consult official authorities.",
            }

    @staticmethod
    async def analyze_market_demand(
        *,
        country: str,
        role: str,
        industry: str,
        primary_role: str,
        seniority_level: str,
        skills: str,
    ) -> dict[str, Any]:
        """Analyze job market demand for a role in a country.

        Args:
            country: Target country.
            role: Role to assess.
            industry: Industry filter.
            primary_role: User's Career DNA role.
            seniority_level: User's seniority.
            skills: User's skills string.

        Returns:
            Dict with demand_level, open_positions_estimate, etc.
        """
        clean_country, _ = sanitize_user_text(
            country, max_length=100, context="demand_country",
        )
        clean_role, _ = sanitize_user_text(
            role or primary_role or "Software Engineer",
            max_length=255, context="demand_role",
        )
        clean_industry, _ = sanitize_user_text(
            industry or "Technology", max_length=200,
            context="demand_industry",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000, context="demand_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=MARKET_DEMAND_PROMPT.format(
                    country=clean_country,
                    role=clean_role,
                    industry=clean_industry,
                    primary_role=primary_role or clean_role,
                    seniority_level=seniority_level or "mid",
                    skills=clean_skills,
                ),
                system_prompt="You are the PathForge Market Demand Analyst.",
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=512,
            )

            _clamp_market_demand(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Market demand for %s in %s completed — "
                "level %s (%.2fs)",
                clean_role, clean_country,
                result.get("demand_level", "unknown"),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Market demand analysis failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "demand_level": "moderate",
                "open_positions_estimate": None,
                "yoy_growth_pct": None,
                "top_employers": None,
                "salary_range_min": None,
                "salary_range_max": None,
                "currency": "EUR",
            }

    # ── Static Helpers ──────────────────────────────────────────

    @staticmethod
    def compute_passport_score(
        *,
        credential_confidence: float,
        visa_eligibility: float,
        demand_level: str,
        purchasing_power_delta: float,
    ) -> dict[str, Any]:
        """Compute composite Career Passport Score™.

        Weighted formula:
            overall = 0.30 × credential
                    + 0.25 × visa
                    + 0.25 × demand
                    + 0.20 × financial

        Args:
            credential_confidence: Credential mapping confidence (0-0.85).
            visa_eligibility: Visa eligibility score (0-0.85).
            demand_level: Market demand level string.
            purchasing_power_delta: Purchasing power impact (%).

        Returns:
            Dict with component scores and overall score.
        """
        credential_score = min(credential_confidence / MAX_PASSPORT_CONFIDENCE, 1.0)
        visa_score = min(visa_eligibility / MAX_PASSPORT_CONFIDENCE, 1.0)
        demand_score = CareerPassportAnalyzer.compute_demand_score(
            demand_level=demand_level,
        )
        financial_score = CareerPassportAnalyzer.compute_financial_score(
            purchasing_power_delta=purchasing_power_delta,
        )

        overall = (
            0.30 * credential_score
            + 0.25 * visa_score
            + 0.25 * demand_score
            + 0.20 * financial_score
        )

        return {
            "credential_score": round(credential_score, 3),
            "visa_score": round(visa_score, 3),
            "demand_score": round(demand_score, 3),
            "financial_score": round(financial_score, 3),
            "overall_score": round(min(overall, 1.0), 3),
        }

    @staticmethod
    def compute_credential_confidence(
        *,
        llm_confidence: float,
        eqf_level_known: bool = True,
        career_dna_completeness: float = 0.5,
    ) -> float:
        """Compute credential mapping confidence, capped at 0.85.

        Formula:
            weighted = 0.50 × llm_confidence
                     + 0.30 × eqf_bonus
                     + 0.20 × career_dna_completeness

        Args:
            llm_confidence: LLM-reported confidence (0-1).
            eqf_level_known: Whether EQF level is standard/known.
            career_dna_completeness: Career DNA profile completeness (0-1).

        Returns:
            Capped confidence from 0.0 to 0.85.
        """
        llm_clamped = max(0.0, min(llm_confidence, MAX_PASSPORT_CONFIDENCE))
        eqf_bonus = 0.8 if eqf_level_known else 0.3
        completeness = max(0.0, min(career_dna_completeness, 1.0))

        raw = 0.50 * llm_clamped + 0.30 * eqf_bonus + 0.20 * completeness
        return round(min(raw, MAX_PASSPORT_CONFIDENCE), 3)

    @staticmethod
    def compute_financial_score(
        *, purchasing_power_delta: float,
    ) -> float:
        """Convert purchasing power delta to normalized score (0-1).

        Mapping:
            delta >= +30%  → 1.0    (very favorable)
            delta   +0-30% → 0.5-1.0 (favorable)
            delta   0%     → 0.5    (neutral)
            delta  -30-0%  → 0.0-0.5 (unfavorable)
            delta <= -30%  → 0.0    (very unfavorable)

        Args:
            purchasing_power_delta: PP delta percentage.

        Returns:
            Normalized financial score (0-1).
        """
        clamped = max(-30.0, min(purchasing_power_delta, 30.0))
        return round((clamped + 30.0) / 60.0, 3)

    @staticmethod
    def compute_demand_score(*, demand_level: str) -> float:
        """Convert demand level string to normalized score (0-1).

        Args:
            demand_level: One of low, moderate, high, very_high.

        Returns:
            Normalized demand score (0-1).
        """
        level_map: dict[str, float] = {
            "low": 0.2,
            "moderate": 0.5,
            "high": 0.75,
            "very_high": 1.0,
        }
        return level_map.get(demand_level, 0.5)


# ── Clamping Validators (module-level, testable) ──────────────


def _clamp_credential_mapping(data: dict[str, Any]) -> None:
    """Validate and clamp credential mapping fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PASSPORT_CONFIDENCE)), 3,
    )

    eqf = data.get("eqf_level", "")
    if eqf not in VALID_EQF_LEVELS:
        data["eqf_level"] = "level_6"  # default to bachelor

    if not data.get("equivalent_level"):
        data["equivalent_level"] = "Unknown equivalent"

    if not data.get("recognition_notes"):
        data["recognition_notes"] = "Verify with the target country's ENIC-NARIC center."


def _clamp_country_comparison(data: dict[str, Any]) -> None:
    """Validate and clamp country comparison fields in-place."""
    for key in ("col_delta_pct", "salary_delta_pct", "purchasing_power_delta"):
        val = data.get(key, 0.0)
        if not isinstance(val, (int, float)):
            val = 0.0
        data[key] = round(float(val), 2)

    demand = data.get("market_demand_level", "moderate")
    if demand not in VALID_DEMAND_LEVELS:
        data["market_demand_level"] = "moderate"


def _clamp_visa_assessment(data: dict[str, Any]) -> None:
    """Validate and clamp visa assessment fields in-place."""
    score = data.get("eligibility_score", 0.0)
    if not isinstance(score, (int, float)):
        score = 0.0
    data["eligibility_score"] = round(
        max(0.0, min(float(score), MAX_PASSPORT_CONFIDENCE)), 3,
    )

    visa_type = data.get("visa_type", "other")
    if visa_type not in VALID_VISA_CATEGORIES:
        data["visa_type"] = "other"

    weeks = data.get("processing_time_weeks")
    if isinstance(weeks, (int, float)):
        data["processing_time_weeks"] = max(1, min(int(weeks), 52))
    else:
        data["processing_time_weeks"] = None


def _clamp_market_demand(data: dict[str, Any]) -> None:
    """Validate and clamp market demand fields in-place."""
    demand = data.get("demand_level", "moderate")
    if demand not in VALID_DEMAND_LEVELS:
        data["demand_level"] = "moderate"

    positions = data.get("open_positions_estimate")
    if isinstance(positions, (int, float)):
        data["open_positions_estimate"] = max(0, int(positions))
    else:
        data["open_positions_estimate"] = None

    for key in ("salary_range_min", "salary_range_max"):
        val = data.get(key)
        if isinstance(val, (int, float)) and val > 0:
            data[key] = round(float(val), 2)
        else:
            data[key] = None

    growth = data.get("yoy_growth_pct")
    if isinstance(growth, (int, float)):
        data["yoy_growth_pct"] = round(float(growth), 2)
    else:
        data["yoy_growth_pct"] = None
