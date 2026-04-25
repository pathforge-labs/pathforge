"""
PathForge — Collective Intelligence Engine™ AI Analyzer
========================================================
LLM-powered career market intelligence pipeline for industry analysis,
salary benchmarking, peer cohort synthesis, and career pulse computation.

LLM Methods (4):
    analyze_industry_snapshot    — Industry health + trend analysis
    analyze_salary_benchmark    — Salary positioning + skill premiums
    analyze_peer_cohort         — Anonymized peer comparison synthesis
    analyze_career_pulse        — Composite career market health score

Static Methods (3):
    compute_pulse_score         — Weighted composite pulse score
    compute_pulse_category      — Score → category classification
    compute_demand_intensity    — Demand level → intensity score

Clamping Validators (4, module-level):
    _clamp_industry_snapshot    — Validate industry snapshot data
    _clamp_salary_benchmark     — Validate salary benchmark data
    _clamp_peer_cohort          — Validate peer cohort data
    _clamp_career_pulse         — Validate career pulse data
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.collective_intelligence_prompts import (
    CAREER_PULSE_PROMPT,
    INDUSTRY_SNAPSHOT_PROMPT,
    PEER_COHORT_PROMPT,
    SALARY_BENCHMARK_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

MAX_CI_CONFIDENCE = 0.85
MIN_COHORT_SIZE = 10

VALID_TREND_DIRECTIONS = frozenset({
    "rising", "stable", "declining", "emerging",
})

VALID_DEMAND_INTENSITIES = frozenset({
    "low", "moderate", "high", "very_high", "critical",
})

VALID_PULSE_CATEGORIES = frozenset({
    "critical", "low", "moderate", "healthy", "thriving",
})


class CollectiveIntelligenceAnalyzer:
    """AI pipeline for Collective Intelligence Engine™ market analysis."""

    # ── LLM Methods ────────────────────────────────────────────

    @staticmethod
    async def analyze_industry_snapshot(
        *,
        industry: str,
        region: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
    ) -> dict[str, Any]:
        """Analyze industry health and trends.

        Industry Trend Radar™ — captures hiring trends, emerging skills,
        salary ranges, and growth projections for the specified industry.

        Args:
            industry: Industry to analyze.
            region: Region for analysis.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's experience in years.

        Returns:
            Dict with trend_direction, demand_intensity, skills, etc.
        """
        clean_industry, _ = sanitize_user_text(
            industry, max_length=200, context="ci_industry",
        )
        clean_region, _ = sanitize_user_text(
            region, max_length=100, context="ci_region",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="ci_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000, context="ci_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=INDUSTRY_SNAPSHOT_PROMPT.format(
                    industry=clean_industry,
                    region=clean_region,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                ),
                system_prompt="You are the PathForge Industry Trend Radar.",
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=1024,
            )

            _clamp_industry_snapshot(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Industry snapshot for %s in %s completed — "
                "trend %s, demand %s (%.2fs)",
                clean_industry, clean_region,
                result.get("trend_direction", "unknown"),
                result.get("demand_intensity", "unknown"),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Industry snapshot failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "trend_direction": "stable",
                "demand_intensity": "moderate",
                "top_emerging_skills": None,
                "declining_skills": None,
                "avg_salary_range_min": None,
                "avg_salary_range_max": None,
                "growth_rate_pct": None,
                "hiring_volume_trend": "Analysis unavailable.",
                "key_insights": None,
                "confidence": 0.0,
            }

    @staticmethod
    async def analyze_salary_benchmark(
        *,
        role: str,
        location: str,
        experience_years: int,
        currency: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
    ) -> dict[str, Any]:
        """Provide personalized salary benchmarking.

        Salary Intelligence Engine™ — analyzes market compensation
        data personalized to the user's Career DNA.

        Args:
            role: Role to benchmark.
            location: Location for benchmark.
            experience_years: Years of experience.
            currency: Preferred currency code.
            primary_role: User's Career DNA role.
            seniority_level: User's seniority level.
            primary_industry: User's industry.
            skills: User's skills string.

        Returns:
            Dict with benchmark_min/median/max, percentile, etc.
        """
        clean_role, _ = sanitize_user_text(
            role or primary_role or "Software Engineer",
            max_length=255, context="ci_salary_role",
        )
        clean_location, _ = sanitize_user_text(
            location or "Netherlands", max_length=200,
            context="ci_salary_location",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="ci_salary_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=SALARY_BENCHMARK_PROMPT.format(
                    role=clean_role,
                    location=clean_location,
                    experience_years=experience_years,
                    currency=currency or "EUR",
                    primary_role=primary_role or clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                ),
                system_prompt=(
                    "You are the PathForge Salary Intelligence Engine."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=768,
            )

            _clamp_salary_benchmark(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Salary benchmark for %s in %s completed — "
                "median %.0f %s (%.2fs)",
                clean_role, clean_location,
                result.get("benchmark_median", 0.0),
                currency or "EUR",
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Salary benchmark failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "benchmark_min": 0.0,
                "benchmark_median": 0.0,
                "benchmark_max": 0.0,
                "user_percentile": None,
                "skill_premium_pct": None,
                "experience_factor": None,
                "negotiation_insights": None,
                "premium_skills": None,
                "confidence": 0.0,
            }

    @staticmethod
    async def analyze_peer_cohort(
        *,
        role: str,
        experience_min: int,
        experience_max: int,
        region: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        user_skills_count: int,
        skills: str,
        years_experience: int,
    ) -> dict[str, Any]:
        """Synthesize peer cohort comparison.

        Peer Cohort Benchmarking™ — AI-synthesized comparison against
        professionals with similar Career DNA profiles with k-anonymity.

        Args:
            role: Role for cohort matching.
            experience_min: Min experience for cohort range.
            experience_max: Max experience for cohort range.
            region: Region filter for cohort.
            primary_role: User's Career DNA role.
            seniority_level: User's seniority level.
            primary_industry: User's industry.
            user_skills_count: Number of user's skills.
            skills: User's skills string.
            years_experience: User's years of experience.

        Returns:
            Dict with cohort_size, rank_percentile, differentiating skills.
        """
        clean_role, _ = sanitize_user_text(
            role or primary_role or "Software Engineer",
            max_length=255, context="ci_peer_role",
        )
        clean_region, _ = sanitize_user_text(
            region or "Global", max_length=100,
            context="ci_peer_region",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="ci_peer_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=PEER_COHORT_PROMPT.format(
                    role=clean_role,
                    experience_min=experience_min,
                    experience_max=experience_max,
                    region=clean_region,
                    primary_role=primary_role or clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    user_skills_count=user_skills_count,
                    skills=clean_skills,
                    years_experience=years_experience,
                ),
                system_prompt=(
                    "You are the PathForge Peer Cohort Benchmarking Engine."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=768,
            )

            _clamp_peer_cohort(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Peer cohort for %s completed — "
                "cohort %d, rank %.0f%% (%.2fs)",
                clean_role,
                result.get("cohort_size", MIN_COHORT_SIZE),
                result.get("user_rank_percentile", 50.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Peer cohort analysis failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "cohort_size": MIN_COHORT_SIZE,
                "user_rank_percentile": 50.0,
                "avg_skills_count": 0.0,
                "avg_experience_years": 0.0,
                "common_transitions": None,
                "top_differentiating_skills": None,
                "skill_gaps_vs_cohort": None,
                "confidence": 0.0,
            }

    @staticmethod
    async def analyze_career_pulse(
        *,
        industry: str,
        region: str,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
        location: str,
    ) -> dict[str, Any]:
        """Compute Career Pulse Index™.

        Composite score (0-100) reflecting real-time career market health
        personalized to the user's Career DNA. No competitor equivalent.

        Args:
            industry: Industry for pulse calculation.
            region: Region for analysis.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's experience in years.
            location: User's location.

        Returns:
            Dict with pulse_score, category, components, actions.
        """
        clean_industry, _ = sanitize_user_text(
            industry or primary_industry or "Technology",
            max_length=200, context="ci_pulse_industry",
        )
        clean_region, _ = sanitize_user_text(
            region or location or "Global",
            max_length=100, context="ci_pulse_region",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="ci_pulse_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="ci_pulse_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=CAREER_PULSE_PROMPT.format(
                    industry=clean_industry,
                    region=clean_region,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                    location=clean_region,
                ),
                system_prompt=(
                    "You are the PathForge Career Pulse Index Calculator."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=1024,
            )

            _clamp_career_pulse(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Career pulse for %s in %s completed — "
                "score %.1f (%s), trend %s (%.2fs)",
                clean_role, clean_region,
                result.get("pulse_score", 50.0),
                result.get("pulse_category", "moderate"),
                result.get("trend_direction", "stable"),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Career pulse failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "pulse_score": 50.0,
                "pulse_category": "moderate",
                "trend_direction": "stable",
                "demand_component": 50.0,
                "salary_component": 50.0,
                "skill_relevance_component": 50.0,
                "trend_component": 50.0,
                "top_opportunities": None,
                "risk_factors": None,
                "recommended_actions": None,
                "summary": "Career Pulse analysis unavailable.",
                "confidence": 0.0,
            }

    # ── Static Helpers ──────────────────────────────────────────

    @staticmethod
    def compute_pulse_score(
        *,
        demand: float,
        salary: float,
        skill_relevance: float,
        trend: float,
    ) -> float:
        """Compute weighted Career Pulse Index score.

        Formula:
            pulse = 0.30 × demand + 0.25 × salary
                  + 0.25 × skill_relevance + 0.20 × trend

        Args:
            demand: Demand component (0-100).
            salary: Salary component (0-100).
            skill_relevance: Skill relevance component (0-100).
            trend: Trend component (0-100).

        Returns:
            Composite pulse score (0-100).
        """
        clamped_demand = max(0.0, min(demand, 100.0))
        clamped_salary = max(0.0, min(salary, 100.0))
        clamped_skill = max(0.0, min(skill_relevance, 100.0))
        clamped_trend = max(0.0, min(trend, 100.0))

        score = (
            0.30 * clamped_demand
            + 0.25 * clamped_salary
            + 0.25 * clamped_skill
            + 0.20 * clamped_trend
        )
        return round(min(score, 100.0), 1)

    @staticmethod
    def compute_pulse_category(*, pulse_score: float) -> str:
        """Map pulse score to category.

        Args:
            pulse_score: Composite pulse score (0-100).

        Returns:
            Category string.
        """
        if pulse_score <= 20.0:
            return "critical"
        if pulse_score <= 40.0:
            return "low"
        if pulse_score <= 60.0:
            return "moderate"
        if pulse_score <= 80.0:
            return "healthy"
        return "thriving"

    @staticmethod
    def compute_demand_intensity(*, demand_score: float) -> str:
        """Map demand score to intensity level.

        Args:
            demand_score: Demand component score (0-100).

        Returns:
            Demand intensity string.
        """
        if demand_score <= 20.0:
            return "low"
        if demand_score <= 40.0:
            return "moderate"
        if demand_score <= 60.0:
            return "high"
        if demand_score <= 80.0:
            return "very_high"
        return "critical"


# ── Clamping Validators (module-level, testable) ──────────────


def _clamp_industry_snapshot(data: dict[str, Any]) -> None:
    """Validate and clamp industry snapshot fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_CI_CONFIDENCE)), 3,
    )

    trend = data.get("trend_direction", "stable")
    if trend not in VALID_TREND_DIRECTIONS:
        data["trend_direction"] = "stable"

    demand = data.get("demand_intensity", "moderate")
    if demand not in VALID_DEMAND_INTENSITIES:
        data["demand_intensity"] = "moderate"

    for key in ("avg_salary_range_min", "avg_salary_range_max"):
        val = data.get(key)
        if isinstance(val, (int, float)) and val > 0:
            data[key] = round(float(val), 2)
        else:
            data[key] = None

    growth = data.get("growth_rate_pct")
    if isinstance(growth, (int, float)):
        data["growth_rate_pct"] = round(float(growth), 2)
    else:
        data["growth_rate_pct"] = None


def _clamp_salary_benchmark(data: dict[str, Any]) -> None:
    """Validate and clamp salary benchmark fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_CI_CONFIDENCE)), 3,
    )

    for key in ("benchmark_min", "benchmark_median", "benchmark_max"):
        val = data.get(key, 0.0)
        if not isinstance(val, (int, float)):
            val = 0.0
        data[key] = round(max(0.0, float(val)), 2)

    percentile = data.get("user_percentile")
    if isinstance(percentile, (int, float)):
        data["user_percentile"] = round(
            max(0.0, min(float(percentile), 100.0)), 1,
        )
    else:
        data["user_percentile"] = None

    premium = data.get("skill_premium_pct")
    if isinstance(premium, (int, float)):
        data["skill_premium_pct"] = round(float(premium), 2)
    else:
        data["skill_premium_pct"] = None

    factor = data.get("experience_factor")
    if isinstance(factor, (int, float)):
        data["experience_factor"] = round(
            max(0.0, min(float(factor), 2.0)), 3,
        )
    else:
        data["experience_factor"] = None


def _clamp_peer_cohort(data: dict[str, Any]) -> None:
    """Validate and clamp peer cohort fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_CI_CONFIDENCE)), 3,
    )

    cohort_size = data.get("cohort_size", MIN_COHORT_SIZE)
    if not isinstance(cohort_size, (int, float)):
        cohort_size = MIN_COHORT_SIZE
    data["cohort_size"] = max(MIN_COHORT_SIZE, int(cohort_size))

    percentile = data.get("user_rank_percentile", 50.0)
    if not isinstance(percentile, (int, float)):
        percentile = 50.0
    data["user_rank_percentile"] = round(
        max(0.0, min(float(percentile), 100.0)), 1,
    )

    avg_skills = data.get("avg_skills_count", 0.0)
    if not isinstance(avg_skills, (int, float)):
        avg_skills = 0.0
    data["avg_skills_count"] = round(max(0.0, float(avg_skills)), 1)

    avg_exp = data.get("avg_experience_years", 0.0)
    if not isinstance(avg_exp, (int, float)):
        avg_exp = 0.0
    data["avg_experience_years"] = round(max(0.0, float(avg_exp)), 1)


def _clamp_career_pulse(data: dict[str, Any]) -> None:
    """Validate and clamp career pulse fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_CI_CONFIDENCE)), 3,
    )

    # Clamp component scores (0-100)
    for key in (
        "demand_component", "salary_component",
        "skill_relevance_component", "trend_component",
    ):
        val = data.get(key, 50.0)
        if not isinstance(val, (int, float)):
            val = 50.0
        data[key] = round(max(0.0, min(float(val), 100.0)), 1)

    # Recompute pulse_score from components
    data["pulse_score"] = CollectiveIntelligenceAnalyzer.compute_pulse_score(
        demand=data["demand_component"],
        salary=data["salary_component"],
        skill_relevance=data["skill_relevance_component"],
        trend=data["trend_component"],
    )

    # Ensure category matches score
    data["pulse_category"] = (
        CollectiveIntelligenceAnalyzer.compute_pulse_category(
            pulse_score=data["pulse_score"],
        )
    )

    trend = data.get("trend_direction", "stable")
    if trend not in VALID_TREND_DIRECTIONS:
        data["trend_direction"] = "stable"
