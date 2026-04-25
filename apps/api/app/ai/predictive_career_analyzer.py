"""
PathForge — Predictive Career Engine™ AI Analyzer
===================================================
LLM-powered predictive career intelligence pipeline for emerging role
detection, disruption forecasting, opportunity surfacing, and composite
career forecast computation.

LLM Methods (4):
    analyze_emerging_roles      — Detect nascent roles matching user skills
    forecast_disruptions        — Predict industry/tech disruptions
    surface_opportunities       — Proactive opportunity identification
    compute_career_forecast     — Composite career outlook score

Static Methods (2):
    compute_outlook_score       — Weighted composite forecast score
    compute_outlook_category    — Score → category classification

Clamping Validators (4, module-level):
    _clamp_emerging_role        — Validate emerging role data
    _clamp_disruption_forecast  — Validate disruption forecast data
    _clamp_opportunity_surface  — Validate opportunity surface data
    _clamp_career_forecast      — Validate career forecast data
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.predictive_career_prompts import (
    CAREER_FORECAST_PROMPT,
    DISRUPTION_FORECAST_PROMPT,
    EMERGING_ROLE_PROMPT,
    OPPORTUNITY_SURFACE_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

MAX_PC_CONFIDENCE = 0.85

VALID_EMERGENCE_STAGES = frozenset({
    "nascent", "growing", "mainstream", "declining",
})

VALID_DISRUPTION_TYPES = frozenset({
    "technology", "regulation", "market_shift",
    "automation", "consolidation",
})

VALID_OPPORTUNITY_TYPES = frozenset({
    "emerging_role", "skill_demand", "industry_growth",
    "geographic_expansion",
})

VALID_OUTLOOK_CATEGORIES = frozenset({
    "critical", "at_risk", "moderate", "favorable", "exceptional",
})


class PredictiveCareerAnalyzer:
    """AI pipeline for Predictive Career Engine™ analysis."""

    # ── LLM Methods ────────────────────────────────────────────

    @staticmethod
    async def analyze_emerging_roles(
        *,
        industry: str,
        region: str,
        min_skill_overlap_pct: float,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
        location: str,
    ) -> list[dict[str, Any]]:
        """Detect emerging roles matching user's Career DNA.

        Emerging Role Radar™ — identifies nascent and growing roles
        before they appear on mainstream job boards.

        Args:
            industry: Industry to scan.
            region: Region for analysis.
            min_skill_overlap_pct: Minimum skill overlap threshold.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's experience in years.
            location: User's location.

        Returns:
            List of dicts with role_title, emergence_stage, overlap, etc.
        """
        clean_industry, _ = sanitize_user_text(
            industry or primary_industry or "Technology",
            max_length=200, context="pc_roles_industry",
        )
        clean_region, _ = sanitize_user_text(
            region or location or "Global",
            max_length=100, context="pc_roles_region",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="pc_roles_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="pc_roles_skills",
        )
        clean_location, _ = sanitize_user_text(
            location or "Global", max_length=200,
            context="pc_roles_location",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=EMERGING_ROLE_PROMPT.format(
                    industry=clean_industry,
                    region=clean_region,
                    min_skill_overlap_pct=min_skill_overlap_pct,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                    location=clean_location,
                ),
                system_prompt=(
                    "You are the PathForge Emerging Role Radar."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=2048,
            )

            roles = result.get("emerging_roles", [])
            if not isinstance(roles, list):
                roles = []

            for role in roles:
                _clamp_emerging_role(role)

            elapsed = time.monotonic() - start
            logger.info(
                "Emerging role scan for %s in %s — "
                "%d roles detected (%.2fs)",
                clean_industry, clean_region,
                len(roles), elapsed,
            )
            return roles

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Emerging role scan failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return []

    @staticmethod
    async def forecast_disruptions(
        *,
        industry: str,
        forecast_horizon_months: int,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
        location: str,
    ) -> list[dict[str, Any]]:
        """Predict industry disruptions affecting user's career.

        Disruption Forecast Engine™ — predicts technology, regulation,
        and market disruptions with severity and timeline estimates.

        Args:
            industry: Industry to analyze.
            forecast_horizon_months: Prediction horizon.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's years of experience.
            location: User's location.

        Returns:
            List of dicts with disruption_title, severity, timeline, etc.
        """
        clean_industry, _ = sanitize_user_text(
            industry or primary_industry or "Technology",
            max_length=200, context="pc_disruption_industry",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="pc_disruption_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="pc_disruption_skills",
        )
        clean_location, _ = sanitize_user_text(
            location or "Global", max_length=200,
            context="pc_disruption_location",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=DISRUPTION_FORECAST_PROMPT.format(
                    industry=clean_industry,
                    forecast_horizon_months=forecast_horizon_months,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                    location=clean_location,
                ),
                system_prompt=(
                    "You are the PathForge Disruption Forecast Engine."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=2048,
            )

            disruptions = result.get("disruptions", [])
            if not isinstance(disruptions, list):
                disruptions = []

            for disruption in disruptions:
                _clamp_disruption_forecast(disruption)

            elapsed = time.monotonic() - start
            logger.info(
                "Disruption forecast for %s — "
                "%d disruptions detected (%.2fs)",
                clean_industry, len(disruptions), elapsed,
            )
            return disruptions

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Disruption forecast failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return []

    @staticmethod
    async def surface_opportunities(
        *,
        industry: str,
        region: str,
        include_cross_border: bool,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
        location: str,
    ) -> list[dict[str, Any]]:
        """Surface proactive career opportunities.

        Proactive Opportunity Engine™ — identifies career opportunities
        before they become obvious to the wider market.

        Args:
            industry: Industry to scan.
            region: Region for analysis.
            include_cross_border: Include international opportunities.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's years of experience.
            location: User's location.

        Returns:
            List of dicts with opportunity_title, type, relevance, etc.
        """
        clean_industry, _ = sanitize_user_text(
            industry or primary_industry or "Technology",
            max_length=200, context="pc_opp_industry",
        )
        clean_region, _ = sanitize_user_text(
            region or location or "Global",
            max_length=100, context="pc_opp_region",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="pc_opp_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="pc_opp_skills",
        )
        clean_location, _ = sanitize_user_text(
            location or "Global", max_length=200,
            context="pc_opp_location",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=OPPORTUNITY_SURFACE_PROMPT.format(
                    industry=clean_industry,
                    region=clean_region,
                    include_cross_border=include_cross_border,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                    location=clean_location,
                ),
                system_prompt=(
                    "You are the PathForge Proactive Opportunity Engine."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=2048,
            )

            opportunities = result.get("opportunities", [])
            if not isinstance(opportunities, list):
                opportunities = []

            for opportunity in opportunities:
                _clamp_opportunity_surface(opportunity)

            elapsed = time.monotonic() - start
            logger.info(
                "Opportunity surface for %s in %s — "
                "%d opportunities detected (%.2fs)",
                clean_industry, clean_region,
                len(opportunities), elapsed,
            )
            return opportunities

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Opportunity surfacing failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return []

    @staticmethod
    async def compute_career_forecast(
        *,
        industry: str,
        region: str,
        forecast_horizon_months: int,
        emerging_roles_count: int,
        disruptions_count: int,
        opportunities_count: int,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
        location: str,
    ) -> dict[str, Any]:
        """Compute Career Forecast Index™.

        Composite forward-looking score (0-100) reflecting predicted
        career trajectory. No competitor equivalent exists.

        Args:
            industry: Industry for forecast.
            region: Region for analysis.
            forecast_horizon_months: Prediction horizon.
            emerging_roles_count: Number of emerging roles found.
            disruptions_count: Number of disruptions detected.
            opportunities_count: Number of opportunities surfaced.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            primary_industry: User's Career DNA industry.
            skills: User's skills string.
            years_experience: User's years of experience.
            location: User's location.

        Returns:
            Dict with outlook_score, category, components, actions.
        """
        clean_industry, _ = sanitize_user_text(
            industry or primary_industry or "Technology",
            max_length=200, context="pc_forecast_industry",
        )
        clean_region, _ = sanitize_user_text(
            region or location or "Global",
            max_length=100, context="pc_forecast_region",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="pc_forecast_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000,
            context="pc_forecast_skills",
        )
        clean_location, _ = sanitize_user_text(
            location or "Global", max_length=200,
            context="pc_forecast_location",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=CAREER_FORECAST_PROMPT.format(
                    industry=clean_industry,
                    region=clean_region,
                    forecast_horizon_months=forecast_horizon_months,
                    emerging_roles_count=emerging_roles_count,
                    disruptions_count=disruptions_count,
                    opportunities_count=opportunities_count,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                    location=clean_location,
                ),
                system_prompt=(
                    "You are the PathForge Career Forecast Index Calculator."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=1024,
            )

            _clamp_career_forecast(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Career forecast for %s in %s — "
                "outlook %.1f (%s) (%.2fs)",
                clean_role, clean_region,
                result.get("outlook_score", 50.0),
                result.get("outlook_category", "moderate"),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Career forecast failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "outlook_score": 50.0,
                "outlook_category": "moderate",
                "forecast_horizon_months": forecast_horizon_months,
                "role_component": 50.0,
                "disruption_component": 50.0,
                "opportunity_component": 50.0,
                "trend_component": 50.0,
                "top_actions": None,
                "key_risks": None,
                "key_opportunities": None,
                "summary": "Career forecast analysis unavailable.",
                "confidence": 0.0,
            }

    # ── Static Helpers ──────────────────────────────────────────

    @staticmethod
    def compute_outlook_score(
        *,
        role: float,
        disruption: float,
        opportunity: float,
        trend: float,
    ) -> float:
        """Compute weighted Career Forecast Index score.

        Formula:
            outlook = 0.30 × role + 0.25 × disruption
                    + 0.25 × opportunity + 0.20 × trend

        Args:
            role: Role component (0-100).
            disruption: Disruption component (0-100, inverse severity).
            opportunity: Opportunity component (0-100).
            trend: Trend component (0-100).

        Returns:
            Composite outlook score (0-100).
        """
        clamped_role = max(0.0, min(role, 100.0))
        clamped_disruption = max(0.0, min(disruption, 100.0))
        clamped_opportunity = max(0.0, min(opportunity, 100.0))
        clamped_trend = max(0.0, min(trend, 100.0))

        score = (
            0.30 * clamped_role
            + 0.25 * clamped_disruption
            + 0.25 * clamped_opportunity
            + 0.20 * clamped_trend
        )
        return round(min(score, 100.0), 1)

    @staticmethod
    def compute_outlook_category(*, outlook_score: float) -> str:
        """Map outlook score to category.

        Args:
            outlook_score: Composite outlook score (0-100).

        Returns:
            Category string.
        """
        if outlook_score <= 20.0:
            return "critical"
        if outlook_score <= 40.0:
            return "at_risk"
        if outlook_score <= 60.0:
            return "moderate"
        if outlook_score <= 80.0:
            return "favorable"
        return "exceptional"


# ── Clamping Validators (module-level, testable) ──────────────


def _clamp_emerging_role(data: dict[str, Any]) -> None:
    """Validate and clamp emerging role fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PC_CONFIDENCE)), 3,
    )

    stage = data.get("emergence_stage", "nascent")
    if stage not in VALID_EMERGENCE_STAGES:
        data["emergence_stage"] = "nascent"

    overlap = data.get("skill_overlap_pct", 0.0)
    if not isinstance(overlap, (int, float)):
        overlap = 0.0
    data["skill_overlap_pct"] = round(
        max(0.0, min(float(overlap), 100.0)), 1,
    )

    growth = data.get("growth_rate_pct", 0.0)
    if not isinstance(growth, (int, float)):
        growth = 0.0
    data["growth_rate_pct"] = round(float(growth), 2)

    months = data.get("time_to_mainstream_months")
    if isinstance(months, (int, float)) and months > 0:
        data["time_to_mainstream_months"] = int(months)
    else:
        data["time_to_mainstream_months"] = None

    for key in ("avg_salary_range_min", "avg_salary_range_max"):
        val = data.get(key)
        if isinstance(val, (int, float)) and val > 0:
            data[key] = round(float(val), 2)
        else:
            data[key] = None


def _clamp_disruption_forecast(data: dict[str, Any]) -> None:
    """Validate and clamp disruption forecast fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PC_CONFIDENCE)), 3,
    )

    disruption_type = data.get("disruption_type", "technology")
    if disruption_type not in VALID_DISRUPTION_TYPES:
        data["disruption_type"] = "technology"

    severity = data.get("severity_score", 50.0)
    if not isinstance(severity, (int, float)):
        severity = 50.0
    data["severity_score"] = round(
        max(0.0, min(float(severity), 100.0)), 1,
    )

    timeline = data.get("timeline_months", 12)
    if not isinstance(timeline, (int, float)):
        timeline = 12
    data["timeline_months"] = max(1, int(timeline))


def _clamp_opportunity_surface(data: dict[str, Any]) -> None:
    """Validate and clamp opportunity surface fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PC_CONFIDENCE)), 3,
    )

    opportunity_type = data.get("opportunity_type", "emerging_role")
    if opportunity_type not in VALID_OPPORTUNITY_TYPES:
        data["opportunity_type"] = "emerging_role"

    relevance = data.get("relevance_score", 0.0)
    if not isinstance(relevance, (int, float)):
        relevance = 0.0
    data["relevance_score"] = round(
        max(0.0, min(float(relevance), 100.0)), 1,
    )


def _clamp_career_forecast(data: dict[str, Any]) -> None:
    """Validate and clamp career forecast fields in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PC_CONFIDENCE)), 3,
    )

    # Clamp component scores (0-100)
    for key in (
        "role_component", "disruption_component",
        "opportunity_component", "trend_component",
    ):
        val = data.get(key, 50.0)
        if not isinstance(val, (int, float)):
            val = 50.0
        data[key] = round(max(0.0, min(float(val), 100.0)), 1)

    # Recompute outlook_score from components
    data["outlook_score"] = PredictiveCareerAnalyzer.compute_outlook_score(
        role=data["role_component"],
        disruption=data["disruption_component"],
        opportunity=data["opportunity_component"],
        trend=data["trend_component"],
    )

    # Ensure category matches score
    data["outlook_category"] = (
        PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=data["outlook_score"],
        )
    )

    horizon = data.get("forecast_horizon_months", 12)
    if not isinstance(horizon, (int, float)):
        horizon = 12
    data["forecast_horizon_months"] = max(3, min(int(horizon), 36))
