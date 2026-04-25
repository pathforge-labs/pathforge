"""
PathForge — Collective Intelligence Engine™ Service
====================================================
Pipeline orchestration for the Collective Intelligence Engine.

Coordinates AI analyzer calls with database persistence,
providing transactional career market intelligence operations.

Service Functions (7):
    get_industry_snapshot         — Industry health analysis
    get_salary_benchmark         — Salary positioning analysis
    get_peer_cohort_analysis     — Peer comparison synthesis
    get_career_pulse             — Career Pulse Index™ computation
    get_ci_dashboard             — Aggregated dashboard
    run_intelligence_scan        — Full intelligence scan
    compare_industries           — Multi-industry comparison
    get_or_update_preferences    — User preferences management
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.collective_intelligence_analyzer import CollectiveIntelligenceAnalyzer
from app.models.career_dna import CareerDNA
from app.models.collective_intelligence import (
    CareerPulseEntry,
    CollectiveIntelligencePreference,
    IndustrySnapshot,
    PeerCohortAnalysis,
    SalaryBenchmark,
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


def _get_skills_count(career_dna: CareerDNA) -> int:
    """Count user's skills from Career DNA genome."""
    if career_dna.skill_genome:
        return len(career_dna.skill_genome)
    return 0


# ── Industry Snapshot ──────────────────────────────────────────


async def get_industry_snapshot(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str,
    region: str,
) -> IndustrySnapshot:
    """Analyze an industry's health and trends.

    Pipeline: fetch Career DNA → call analyzer → persist → return.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry to analyze.
        region: Region for analysis.

    Returns:
        Persisted IndustrySnapshot record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
        industry=industry,
        region=region,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
    )

    snapshot = IndustrySnapshot(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        industry=industry,
        region=region,
        trend_direction=result.get("trend_direction", "stable"),
        demand_intensity=result.get("demand_intensity", "moderate"),
        top_emerging_skills=result.get("top_emerging_skills"),
        declining_skills=result.get("declining_skills"),
        avg_salary_range_min=result.get("avg_salary_range_min"),
        avg_salary_range_max=result.get("avg_salary_range_max"),
        growth_rate_pct=result.get("growth_rate_pct"),
        hiring_volume_trend=result.get("hiring_volume_trend"),
        key_insights=result.get("key_insights"),
        confidence_score=result.get("confidence", 0.0),
    )

    database.add(snapshot)
    await database.commit()
    await database.refresh(snapshot)
    return snapshot


# ── Salary Benchmark ───────────────────────────────────────────


async def get_salary_benchmark(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    role: str | None = None,
    location: str | None = None,
    experience_years: int | None = None,
    currency: str = "EUR",
) -> SalaryBenchmark:
    """Get personalized salary benchmarking.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        role: Role to benchmark (defaults to Career DNA role).
        location: Location (defaults to Career DNA location).
        experience_years: Experience override.
        currency: Preferred currency code.

    Returns:
        Persisted SalaryBenchmark record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    effective_role = role or career_dna.primary_role or "Software Engineer"
    effective_location = location or career_dna.location or "Netherlands"
    effective_years = (
        experience_years
        if experience_years is not None
        else _get_years_experience(career_dna)
    )

    result = await CollectiveIntelligenceAnalyzer.analyze_salary_benchmark(
        role=effective_role,
        location=effective_location,
        experience_years=effective_years,
        currency=currency,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
    )

    benchmark = SalaryBenchmark(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        role=effective_role,
        location=effective_location,
        experience_years=effective_years,
        benchmark_min=result.get("benchmark_min", 0.0),
        benchmark_median=result.get("benchmark_median", 0.0),
        benchmark_max=result.get("benchmark_max", 0.0),
        currency=currency,
        user_percentile=result.get("user_percentile"),
        skill_premium_pct=result.get("skill_premium_pct"),
        experience_factor=result.get("experience_factor"),
        negotiation_insights=result.get("negotiation_insights"),
        premium_skills=result.get("premium_skills"),
        confidence_score=result.get("confidence", 0.0),
    )

    database.add(benchmark)
    await database.commit()
    await database.refresh(benchmark)
    return benchmark


# ── Peer Cohort Analysis ──────────────────────────────────────


async def get_peer_cohort_analysis(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    role: str | None = None,
    experience_range_min: int | None = None,
    experience_range_max: int | None = None,
    region: str | None = None,
) -> PeerCohortAnalysis:
    """Synthesize peer cohort comparison.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        role: Role for cohort matching.
        experience_range_min: Min years experience.
        experience_range_max: Max years experience.
        region: Region filter.

    Returns:
        Persisted PeerCohortAnalysis record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    years_exp = _get_years_experience(career_dna)
    effective_min = experience_range_min if experience_range_min is not None else max(0, years_exp - 2)
    effective_max = experience_range_max if experience_range_max is not None else years_exp + 2

    result = await CollectiveIntelligenceAnalyzer.analyze_peer_cohort(
        role=role or career_dna.primary_role or "Software Engineer",
        experience_min=effective_min,
        experience_max=effective_max,
        region=region or career_dna.location or "Global",
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        user_skills_count=_get_skills_count(career_dna),
        skills=_format_skills_for_prompt(career_dna),
        years_experience=years_exp,
    )

    cohort_criteria: dict[str, Any] = {
        "role": role or career_dna.primary_role or "Software Engineer",
        "experience_range": f"{effective_min}-{effective_max}",
        "region": region or career_dna.location or "Global",
        "industry": career_dna.primary_industry or "Technology",
    }

    analysis = PeerCohortAnalysis(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        cohort_criteria=cohort_criteria,
        cohort_size=result.get("cohort_size", 10),
        user_rank_percentile=result.get("user_rank_percentile", 50.0),
        avg_skills_count=result.get("avg_skills_count", 0.0),
        user_skills_count=_get_skills_count(career_dna),
        avg_experience_years=result.get("avg_experience_years", 0.0),
        common_transitions=result.get("common_transitions"),
        top_differentiating_skills=result.get("top_differentiating_skills"),
        skill_gaps_vs_cohort=result.get("skill_gaps_vs_cohort"),
        confidence_score=result.get("confidence", 0.0),
    )

    database.add(analysis)
    await database.commit()
    await database.refresh(analysis)
    return analysis


# ── Career Pulse ──────────────────────────────────────────────


async def get_career_pulse(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
) -> CareerPulseEntry:
    """Compute Career Pulse Index™.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.

    Returns:
        Persisted CareerPulseEntry record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await CollectiveIntelligenceAnalyzer.analyze_career_pulse(
        industry=industry or career_dna.primary_industry or "Technology",
        region=region or career_dna.location or "Global",
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        location=career_dna.location or "Global",
    )

    pulse_entry = CareerPulseEntry(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        pulse_score=result.get("pulse_score", 50.0),
        pulse_category=result.get("pulse_category", "moderate"),
        trend_direction=result.get("trend_direction", "stable"),
        demand_component=result.get("demand_component", 50.0),
        salary_component=result.get("salary_component", 50.0),
        skill_relevance_component=result.get("skill_relevance_component", 50.0),
        trend_component=result.get("trend_component", 50.0),
        top_opportunities=result.get("top_opportunities"),
        risk_factors=result.get("risk_factors"),
        recommended_actions=result.get("recommended_actions"),
        summary=result.get("summary"),
        confidence_score=result.get("confidence", 0.0),
    )

    database.add(pulse_entry)
    await database.commit()
    await database.refresh(pulse_entry)
    return pulse_entry


# ── Dashboard ──────────────────────────────────────────────────


async def get_ci_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get Collective Intelligence dashboard aggregate.

    Args:
        database: Async database session.
        user_id: Current user's UUID.

    Returns:
        Dict with latest pulse, snapshots, benchmarks, cohorts, prefs.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    # Latest career pulse
    pulse_result = await database.execute(
        select(CareerPulseEntry)
        .where(CareerPulseEntry.career_dna_id == str(career_dna.id))
        .order_by(CareerPulseEntry.created_at.desc())
        .limit(1)
    )
    latest_pulse = pulse_result.scalar_one_or_none()

    # Recent industry snapshots (last 5)
    snapshots_result = await database.execute(
        select(IndustrySnapshot)
        .where(IndustrySnapshot.career_dna_id == str(career_dna.id))
        .order_by(IndustrySnapshot.created_at.desc())
        .limit(5)
    )
    industry_snapshots = list(snapshots_result.scalars().all())

    # Recent salary benchmarks (last 5)
    benchmarks_result = await database.execute(
        select(SalaryBenchmark)
        .where(SalaryBenchmark.career_dna_id == str(career_dna.id))
        .order_by(SalaryBenchmark.created_at.desc())
        .limit(5)
    )
    salary_benchmarks = list(benchmarks_result.scalars().all())

    # Recent peer cohort analyses (last 3)
    cohorts_result = await database.execute(
        select(PeerCohortAnalysis)
        .where(PeerCohortAnalysis.career_dna_id == str(career_dna.id))
        .order_by(PeerCohortAnalysis.created_at.desc())
        .limit(3)
    )
    peer_cohorts = list(cohorts_result.scalars().all())

    # Preferences
    prefs_result = await database.execute(
        select(CollectiveIntelligencePreference)
        .where(
            CollectiveIntelligencePreference.career_dna_id
            == str(career_dna.id)
        )
    )
    preferences = prefs_result.scalar_one_or_none()

    return {
        "latest_pulse": latest_pulse,
        "industry_snapshots": industry_snapshots,
        "salary_benchmarks": salary_benchmarks,
        "peer_cohort_analyses": peer_cohorts,
        "preferences": preferences,
    }


# ── Full Intelligence Scan ─────────────────────────────────────


async def run_intelligence_scan(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industry: str | None = None,
    region: str | None = None,
    currency: str = "EUR",
) -> dict[str, Any]:
    """Execute full intelligence scan.

    Runs all 4 analyses in sequence: pulse → industry → salary → peer.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industry: Industry override.
        region: Region override.
        currency: Preferred currency.

    Returns:
        Dict with all scan results.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    effective_industry = industry or career_dna.primary_industry or "Technology"
    effective_region = region or career_dna.location or "Global"

    career_pulse = await get_career_pulse(
        database, user_id=user_id,
        industry=effective_industry, region=effective_region,
    )

    industry_snapshot = await get_industry_snapshot(
        database, user_id=user_id,
        industry=effective_industry, region=effective_region,
    )

    salary_benchmark = await get_salary_benchmark(
        database, user_id=user_id,
        currency=currency,
    )

    peer_cohort = await get_peer_cohort_analysis(
        database, user_id=user_id,
    )

    return {
        "career_pulse": career_pulse,
        "industry_snapshot": industry_snapshot,
        "salary_benchmark": salary_benchmark,
        "peer_cohort": peer_cohort,
    }


# ── Industry Comparison ───────────────────────────────────────


async def compare_industries(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    industries: list[str],
    region: str,
) -> dict[str, Any]:
    """Compare multiple industries side-by-side.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        industries: Industries to compare (2-5).
        region: Region for comparison.

    Returns:
        Dict with snapshots and recommended industry.

    Raises:
        ValueError: If CareerDNA not found or too many industries.
    """
    if len(industries) > 5:
        raise ValueError("Maximum 5 industries for comparison.")
    if len(industries) < 2:
        raise ValueError("At least 2 industries required for comparison.")

    snapshots: list[IndustrySnapshot] = []
    for industry in industries:
        snapshot = await get_industry_snapshot(
            database, user_id=user_id, industry=industry, region=region,
        )
        snapshots.append(snapshot)

    # Determine recommended industry by highest confidence + demand
    best_snapshot: IndustrySnapshot | None = None
    best_score = -1.0
    for snapshot in snapshots:
        demand_map: dict[str, float] = {
            "low": 0.2,
            "moderate": 0.5,
            "high": 0.75,
            "very_high": 0.9,
            "critical": 1.0,
        }
        demand_score = demand_map.get(snapshot.demand_intensity, 0.5)
        trend_map: dict[str, float] = {
            "declining": 0.2,
            "stable": 0.5,
            "rising": 0.8,
            "emerging": 0.9,
        }
        trend_score = trend_map.get(snapshot.trend_direction, 0.5)
        composite = demand_score * 0.5 + trend_score * 0.5
        if composite > best_score:
            best_score = composite
            best_snapshot = snapshot

    recommended = (
        best_snapshot.industry if best_snapshot else industries[0]
    )
    reasoning = (
        f"{recommended} shows the strongest combination of demand "
        f"({best_snapshot.demand_intensity if best_snapshot else 'moderate'}) "
        f"and trend direction "
        f"({best_snapshot.trend_direction if best_snapshot else 'stable'}) "
        f"for your Career DNA profile."
    )

    return {
        "snapshots": snapshots,
        "recommended_industry": recommended,
        "recommendation_reasoning": reasoning,
    }


# ── Preferences ────────────────────────────────────────────────


async def get_or_update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    updates: dict[str, Any] | None = None,
) -> CollectiveIntelligencePreference:
    """Get or update user CI preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        updates: Optional dict of preference fields to update.

    Returns:
        Current or updated CollectiveIntelligencePreference record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await database.execute(
        select(CollectiveIntelligencePreference)
        .where(
            CollectiveIntelligencePreference.career_dna_id
            == str(career_dna.id)
        )
    )
    preference = result.scalar_one_or_none()

    if preference is None:
        preference = CollectiveIntelligencePreference(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
        )
        database.add(preference)

    if updates:
        allowed_fields = {
            "include_industry_pulse",
            "include_salary_benchmarks",
            "include_peer_analysis",
            "preferred_industries",
            "preferred_locations",
            "preferred_currency",
        }
        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                # Convert lists to JSON-compatible dicts
                if (
                    key in ("preferred_industries", "preferred_locations")
                    and isinstance(value, list)
                ):
                    value = {"items": value}
                setattr(preference, key, value)

    await database.commit()
    await database.refresh(preference)
    return preference
