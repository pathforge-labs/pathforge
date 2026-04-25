"""
PathForge — Predictive Career Engine™ Service
===============================================
Pipeline orchestration for the Predictive Career Engine.

Coordinates AI analyzer calls with database persistence,
providing transactional predictive career intelligence operations.

Service Functions (7):
    scan_emerging_roles          — Detect emerging roles
    get_disruption_forecasts     — Predict disruptions
    get_opportunity_surfaces     — Surface opportunities
    get_career_forecast          — Compute Career Forecast Index™
    get_pc_dashboard             — Aggregated dashboard
    run_predictive_scan          — Full predictive scan
    get_or_update_preferences    — User preferences management
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.predictive_career_analyzer import PredictiveCareerAnalyzer
from app.models.career_dna import CareerDNA
from app.models.predictive_career import (
    CareerForecast,
    DisruptionForecast,
    EmergingRole,
    OpportunitySurface,
    PredictiveCareerPreference,
)

logger = logging.getLogger(__name__)


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_context(
    database: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with eager-loaded skill genome."""
    result = await database.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(
            selectinload(CareerDNA.skill_genome),
            selectinload(CareerDNA.experience_blueprint),
        )
    )
    return result.scalar_one_or_none()


def _format_skills_for_prompt(career_dna: CareerDNA) -> str:
    """Format Career DNA skill genome as comma-separated string."""
    if not career_dna.skill_genome:
        return "No skills recorded"
    return ", ".join(
        f"{entry.skill_name} ({entry.proficiency_level})"
        for entry in career_dna.skill_genome
    )


def _get_years_experience(career_dna: CareerDNA) -> int:
    """Estimate years of experience from Career DNA context."""
    if (
        hasattr(career_dna, "experience_blueprint")
        and career_dna.experience_blueprint
    ):
        blueprint = career_dna.experience_blueprint
        if hasattr(blueprint, "total_years"):
            return max(1, int(blueprint.total_years))
    return 3  # Default assumption


# ── Emerging Role Radar™ ──────────────────────────────────────


async def scan_emerging_roles(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
    min_skill_overlap_pct: float = 50.0,
) -> list[EmergingRole]:
    """Detect emerging roles matching user's Career DNA.

    Pipeline: fetch Career DNA → call analyzer → persist each → return.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.
        min_skill_overlap_pct: Minimum skill overlap threshold.

    Returns:
        List of persisted EmergingRole records.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    results = await PredictiveCareerAnalyzer.analyze_emerging_roles(
        industry=industry or career_dna.primary_industry or "Technology",
        region=region or career_dna.location or "Global",
        min_skill_overlap_pct=min_skill_overlap_pct,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        location=career_dna.location or "Global",
    )

    roles: list[EmergingRole] = []
    for role_data in results:
        role = EmergingRole(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
            role_title=role_data.get("role_title", "Unknown Role"),
            industry=role_data.get(
                "industry",
                industry or career_dna.primary_industry or "Technology",
            ),
            emergence_stage=role_data.get("emergence_stage", "nascent"),
            growth_rate_pct=role_data.get("growth_rate_pct", 0.0),
            skill_overlap_pct=role_data.get("skill_overlap_pct", 0.0),
            time_to_mainstream_months=role_data.get(
                "time_to_mainstream_months",
            ),
            required_new_skills=role_data.get("required_new_skills"),
            transferable_skills=role_data.get("transferable_skills"),
            avg_salary_range_min=role_data.get("avg_salary_range_min"),
            avg_salary_range_max=role_data.get("avg_salary_range_max"),
            key_employers=role_data.get("key_employers"),
            reasoning=role_data.get("reasoning"),
            confidence_score=role_data.get("confidence", 0.0),
        )
        database.add(role)
        roles.append(role)

    await database.commit()
    for role in roles:
        await database.refresh(role)
    return roles


# ── Disruption Forecast Engine™ ──────────────────────────────


async def get_disruption_forecasts(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    forecast_horizon_months: int = 12,
) -> list[DisruptionForecast]:
    """Predict disruptions affecting user's career.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        forecast_horizon_months: Prediction horizon.

    Returns:
        List of persisted DisruptionForecast records.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    results = await PredictiveCareerAnalyzer.forecast_disruptions(
        industry=industry or career_dna.primary_industry or "Technology",
        forecast_horizon_months=forecast_horizon_months,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        location=career_dna.location or "Global",
    )

    forecasts: list[DisruptionForecast] = []
    for forecast_data in results:
        forecast = DisruptionForecast(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
            disruption_title=forecast_data.get(
                "disruption_title", "Unknown Disruption",
            ),
            disruption_type=forecast_data.get(
                "disruption_type", "technology",
            ),
            industry=forecast_data.get(
                "industry",
                industry or career_dna.primary_industry or "Technology",
            ),
            severity_score=forecast_data.get("severity_score", 50.0),
            timeline_months=forecast_data.get("timeline_months", 12),
            impact_on_user=forecast_data.get("impact_on_user"),
            affected_skills=forecast_data.get("affected_skills"),
            mitigation_strategies=forecast_data.get(
                "mitigation_strategies",
            ),
            opportunity_from_disruption=forecast_data.get(
                "opportunity_from_disruption",
            ),
            confidence_score=forecast_data.get("confidence", 0.0),
        )
        database.add(forecast)
        forecasts.append(forecast)

    await database.commit()
    for forecast in forecasts:
        await database.refresh(forecast)
    return forecasts


# ── Opportunity Surfacing ────────────────────────────────────


async def get_opportunity_surfaces(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
    include_cross_border: bool = True,
) -> list[OpportunitySurface]:
    """Surface proactive career opportunities.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.
        include_cross_border: Include international opportunities.

    Returns:
        List of persisted OpportunitySurface records.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    results = await PredictiveCareerAnalyzer.surface_opportunities(
        industry=industry or career_dna.primary_industry or "Technology",
        region=region or career_dna.location or "Global",
        include_cross_border=include_cross_border,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        location=career_dna.location or "Global",
    )

    opportunities: list[OpportunitySurface] = []
    for opp_data in results:
        opportunity = OpportunitySurface(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
            opportunity_title=opp_data.get(
                "opportunity_title", "Unknown Opportunity",
            ),
            opportunity_type=opp_data.get(
                "opportunity_type", "emerging_role",
            ),
            source_signal=opp_data.get(
                "source_signal", "market_analysis",
            ),
            relevance_score=opp_data.get("relevance_score", 0.0),
            action_items=opp_data.get("action_items"),
            required_skills=opp_data.get("required_skills"),
            skill_gap_analysis=opp_data.get("skill_gap_analysis"),
            time_sensitivity=opp_data.get("time_sensitivity"),
            reasoning=opp_data.get("reasoning"),
            confidence_score=opp_data.get("confidence", 0.0),
        )
        database.add(opportunity)
        opportunities.append(opportunity)

    await database.commit()
    for opportunity in opportunities:
        await database.refresh(opportunity)
    return opportunities


# ── Career Forecast Index™ ───────────────────────────────────


async def get_career_forecast(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
    forecast_horizon_months: int = 12,
    emerging_roles_count: int = 0,
    disruptions_count: int = 0,
    opportunities_count: int = 0,
) -> CareerForecast:
    """Compute Career Forecast Index™.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.
        forecast_horizon_months: Prediction horizon.
        emerging_roles_count: Number of emerging roles found.
        disruptions_count: Number of disruptions detected.
        opportunities_count: Number of opportunities surfaced.

    Returns:
        Persisted CareerForecast record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await PredictiveCareerAnalyzer.compute_career_forecast(
        industry=industry or career_dna.primary_industry or "Technology",
        region=region or career_dna.location or "Global",
        forecast_horizon_months=forecast_horizon_months,
        emerging_roles_count=emerging_roles_count,
        disruptions_count=disruptions_count,
        opportunities_count=opportunities_count,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        location=career_dna.location or "Global",
    )

    forecast = CareerForecast(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        outlook_score=result.get("outlook_score", 50.0),
        outlook_category=result.get("outlook_category", "moderate"),
        forecast_horizon_months=result.get(
            "forecast_horizon_months", forecast_horizon_months,
        ),
        role_component=result.get("role_component", 50.0),
        disruption_component=result.get("disruption_component", 50.0),
        opportunity_component=result.get("opportunity_component", 50.0),
        trend_component=result.get("trend_component", 50.0),
        top_actions=result.get("top_actions"),
        key_risks=result.get("key_risks"),
        key_opportunities=result.get("key_opportunities"),
        summary=result.get("summary"),
        confidence_score=result.get("confidence", 0.0),
    )

    database.add(forecast)
    await database.commit()
    await database.refresh(forecast)
    return forecast


# ── Dashboard ────────────────────────────────────────────────


async def get_pc_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get Predictive Career dashboard aggregate.

    Args:
        database: Async database session.
        user_id: Current user's UUID.

    Returns:
        Dict with latest forecast, roles, disruptions, opportunities, prefs.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    # Latest career forecast
    forecast_result = await database.execute(
        select(CareerForecast)
        .where(CareerForecast.career_dna_id == str(career_dna.id))
        .order_by(CareerForecast.created_at.desc())
        .limit(1)
    )
    latest_forecast = forecast_result.scalar_one_or_none()

    # Recent emerging roles (last 10)
    roles_result = await database.execute(
        select(EmergingRole)
        .where(EmergingRole.career_dna_id == str(career_dna.id))
        .order_by(EmergingRole.created_at.desc())
        .limit(10)
    )
    emerging_roles = list(roles_result.scalars().all())

    # Recent disruption forecasts (last 5)
    forecasts_result = await database.execute(
        select(DisruptionForecast)
        .where(DisruptionForecast.career_dna_id == str(career_dna.id))
        .order_by(DisruptionForecast.created_at.desc())
        .limit(5)
    )
    disruption_forecasts = list(forecasts_result.scalars().all())

    # Recent opportunity surfaces (last 10)
    opps_result = await database.execute(
        select(OpportunitySurface)
        .where(OpportunitySurface.career_dna_id == str(career_dna.id))
        .order_by(OpportunitySurface.created_at.desc())
        .limit(10)
    )
    opportunity_surfaces = list(opps_result.scalars().all())

    # Preferences
    prefs_result = await database.execute(
        select(PredictiveCareerPreference)
        .where(
            PredictiveCareerPreference.career_dna_id
            == str(career_dna.id)
        )
    )
    preferences = prefs_result.scalar_one_or_none()

    return {
        "latest_forecast": latest_forecast,
        "emerging_roles": emerging_roles,
        "disruption_forecasts": disruption_forecasts,
        "opportunity_surfaces": opportunity_surfaces,
        "preferences": preferences,
    }


# ── Full Predictive Scan ─────────────────────────────────────


async def run_predictive_scan(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
    forecast_horizon_months: int = 12,
) -> dict[str, Any]:
    """Execute full predictive scan.

    Runs all 3 analyses in sequence: roles → disruptions → opportunities
    → forecast (using counts from previous steps).

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.
        forecast_horizon_months: Prediction horizon.

    Returns:
        Dict with all scan results.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    emerging_roles = await scan_emerging_roles(
        database, user_id=user_id,
        industry=industry, region=region,
    )

    disruption_forecasts = await get_disruption_forecasts(
        database, user_id=user_id,
        industry=industry,
        forecast_horizon_months=forecast_horizon_months,
    )

    opportunity_surfaces = await get_opportunity_surfaces(
        database, user_id=user_id,
        industry=industry, region=region,
    )

    career_forecast = await get_career_forecast(
        database, user_id=user_id,
        industry=industry, region=region,
        forecast_horizon_months=forecast_horizon_months,
        emerging_roles_count=len(emerging_roles),
        disruptions_count=len(disruption_forecasts),
        opportunities_count=len(opportunity_surfaces),
    )

    return {
        "career_forecast": career_forecast,
        "emerging_roles": emerging_roles,
        "disruption_forecasts": disruption_forecasts,
        "opportunity_surfaces": opportunity_surfaces,
    }


# ── Preferences ──────────────────────────────────────────────


async def get_or_update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    updates: dict[str, Any] | None = None,
) -> PredictiveCareerPreference:
    """Get or update user PC preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        updates: Optional dict of preference fields to update.

    Returns:
        Current or updated PredictiveCareerPreference record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await database.execute(
        select(PredictiveCareerPreference)
        .where(
            PredictiveCareerPreference.career_dna_id
            == str(career_dna.id)
        )
    )
    preference = result.scalar_one_or_none()

    if preference is None:
        preference = PredictiveCareerPreference(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
        )
        database.add(preference)

    if updates:
        allowed_fields = {
            "forecast_horizon_months",
            "include_emerging_roles",
            "include_disruption_alerts",
            "include_opportunities",
            "risk_tolerance",
            "focus_industries",
            "focus_regions",
        }
        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                # Convert lists to JSON-compatible dicts
                if (
                    key in ("focus_industries", "focus_regions")
                    and isinstance(value, list)
                ):
                    value = {"items": value}
                setattr(preference, key, value)

    await database.commit()
    await database.refresh(preference)
    return preference
