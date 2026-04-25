"""
PathForge — Cross-Border Career Passport™ Service
====================================================
Pipeline orchestration for the Career Passport.

Coordinates AI analyzer calls with database persistence,
Career DNA context extraction, and response composition.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.career_passport_analyzer import CareerPassportAnalyzer
from app.models.career_dna import CareerDNA
from app.models.career_passport import (
    CareerPassportPreference,
    CountryComparison,
    CredentialMapping,
    MarketDemandEntry,
    VisaAssessment,
)
from app.schemas.career_passport import CareerPassportPreferenceUpdate

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
    if hasattr(career_dna, "experience_blueprint") and career_dna.experience_blueprint:
        blueprint = career_dna.experience_blueprint
        if hasattr(blueprint, "total_years"):
            return max(1, int(blueprint.total_years))
    return 3  # Default assumption


def _get_salary_context(career_dna: CareerDNA) -> str:
    """Extract salary context string from Career DNA."""
    if hasattr(career_dna, "current_salary") and career_dna.current_salary:
        return f"{career_dna.current_salary} {getattr(career_dna, 'salary_currency', 'EUR')}"
    return "Not provided"


def _get_education_level(career_dna: CareerDNA) -> str:
    """Extract education level from Career DNA."""
    if hasattr(career_dna, "education_level") and career_dna.education_level:
        return str(career_dna.education_level)
    return "bachelor"


# ── Credential Mapping ────────────────────────────────────────


async def map_credential(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_qualification: str,
    source_country: str,
    target_country: str,
) -> CredentialMapping:
    """Map a qualification to its international equivalent.

    Pipeline: fetch Career DNA → call analyzer → persist → return.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        source_qualification: Qualification to map.
        source_country: Country where obtained.
        target_country: Target country.

    Returns:
        Persisted CredentialMapping record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await CareerPassportAnalyzer.analyze_credential_mapping(
        source_qualification=source_qualification,
        source_country=source_country,
        target_country=target_country,
        primary_role=career_dna.primary_role or "Software Engineer",
        primary_industry=career_dna.primary_industry or "Technology",
        years_experience=_get_years_experience(career_dna),
    )

    confidence = CareerPassportAnalyzer.compute_credential_confidence(
        llm_confidence=result.get("confidence", 0.0),
        eqf_level_known=result.get("eqf_level", "level_6") in {
            "level_1", "level_2", "level_3", "level_4",
            "level_5", "level_6", "level_7", "level_8",
        },
        career_dna_completeness=float(getattr(career_dna, "profile_completeness", 0.5) or 0.5),
    )

    mapping = CredentialMapping(
        career_dna_id=career_dna.id,
        user_id=user_id,
        source_qualification=source_qualification,
        source_country=source_country,
        target_country=target_country,
        equivalent_level=result.get("equivalent_level", "Unknown"),
        eqf_level=result.get("eqf_level", "level_6"),
        recognition_notes=result.get("recognition_notes"),
        framework_reference=result.get("framework_reference"),
        confidence_score=confidence,
    )

    database.add(mapping)
    await database.commit()
    await database.refresh(mapping)
    return mapping


# ── Country Comparison ─────────────────────────────────────────


async def compare_countries(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_country: str,
    target_country: str,
) -> CountryComparison:
    """Compare two countries for career mobility.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        source_country: Current country.
        target_country: Target country.

    Returns:
        Persisted CountryComparison record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await CareerPassportAnalyzer.analyze_country_comparison(
        source_country=source_country,
        target_country=target_country,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        years_experience=_get_years_experience(career_dna),
        salary_context=_get_salary_context(career_dna),
    )

    comparison = CountryComparison(
        career_dna_id=career_dna.id,
        user_id=user_id,
        source_country=source_country,
        target_country=target_country,
        col_delta_pct=result.get("col_delta_pct", 0.0),
        salary_delta_pct=result.get("salary_delta_pct", 0.0),
        purchasing_power_delta=result.get("purchasing_power_delta", 0.0),
        tax_impact_notes=result.get("tax_impact_notes"),
        market_demand_level=result.get("market_demand_level", "moderate"),
        detailed_breakdown=result.get("detailed_breakdown"),
    )

    database.add(comparison)
    await database.commit()
    await database.refresh(comparison)
    return comparison


# ── Multi-Country Comparison ──────────────────────────────────


async def compare_multiple_countries(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_country: str,
    target_countries: list[str],
) -> dict[str, Any]:
    """Compare up to 5 countries side-by-side.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        source_country: Current country.
        target_countries: Target countries (max 5).

    Returns:
        Dict with comparisons list, passport_scores, and recommendation.

    Raises:
        ValueError: If CareerDNA not found or too many countries.
    """
    if len(target_countries) > 5:
        raise ValueError("Maximum 5 target countries allowed.")

    comparisons: list[CountryComparison] = []
    scores: list[dict[str, Any]] = []

    for target in target_countries:
        comparison = await compare_countries(
            database,
            user_id=user_id,
            source_country=source_country,
            target_country=target,
        )
        comparisons.append(comparison)

    # Compute passport scores for each (requires credential + visa data)
    for comparison in comparisons:
        score_data = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=0.5,  # Default if no credential mapping
            visa_eligibility=0.5,  # Default if no visa assessment
            demand_level=comparison.market_demand_level,
            purchasing_power_delta=comparison.purchasing_power_delta,
        )
        score_data["target_country"] = comparison.target_country
        scores.append(score_data)

    # Sort by overall score, recommend highest
    scores.sort(key=lambda item: item.get("overall_score", 0), reverse=True)
    recommended = scores[0]["target_country"] if scores else None

    return {
        "comparisons": comparisons,
        "passport_scores": scores,
        "recommended_country": recommended,
        "recommendation_reasoning": (
            f"{recommended} scores highest across credential, visa, "
            f"demand, and financial dimensions."
            if recommended else None
        ),
    }


# ── Visa Assessment ────────────────────────────────────────────


async def assess_visa(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    nationality: str,
    target_country: str,
) -> VisaAssessment:
    """Assess visa feasibility for a target country.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        nationality: User's nationality.
        target_country: Target country.

    Returns:
        Persisted VisaAssessment record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await CareerPassportAnalyzer.analyze_visa_feasibility(
        nationality=nationality,
        target_country=target_country,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        primary_industry=career_dna.primary_industry or "Technology",
        years_experience=_get_years_experience(career_dna),
        education_level=_get_education_level(career_dna),
    )

    assessment = VisaAssessment(
        career_dna_id=career_dna.id,
        user_id=user_id,
        nationality=nationality,
        target_country=target_country,
        visa_type=result.get("visa_type", "other"),
        eligibility_score=result.get("eligibility_score", 0.0),
        requirements=result.get("requirements"),
        processing_time_weeks=result.get("processing_time_weeks"),
        estimated_cost=result.get("estimated_cost"),
        notes=result.get("notes"),
    )

    database.add(assessment)
    await database.commit()
    await database.refresh(assessment)
    return assessment


# ── Market Demand ──────────────────────────────────────────────


async def get_market_demand(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    country: str,
    role: str | None = None,
    industry: str | None = None,
) -> MarketDemandEntry:
    """Get market demand for a role in a country.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        country: Target country.
        role: Specific role (defaults to Career DNA role).
        industry: Industry filter.

    Returns:
        Persisted MarketDemandEntry record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    effective_role = role or career_dna.primary_role or "Software Engineer"
    effective_industry = industry or career_dna.primary_industry or "Technology"

    result = await CareerPassportAnalyzer.analyze_market_demand(
        country=country,
        role=effective_role,
        industry=effective_industry,
        primary_role=career_dna.primary_role or "Software Engineer",
        seniority_level=career_dna.seniority_level or "mid",
        skills=_format_skills_for_prompt(career_dna),
    )

    entry = MarketDemandEntry(
        career_dna_id=career_dna.id,
        user_id=user_id,
        country=country,
        role=effective_role,
        industry=effective_industry,
        demand_level=result.get("demand_level", "moderate"),
        open_positions_estimate=result.get("open_positions_estimate"),
        yoy_growth_pct=result.get("yoy_growth_pct"),
        top_employers=result.get("top_employers"),
        salary_range_min=result.get("salary_range_min"),
        salary_range_max=result.get("salary_range_max"),
        currency=result.get("currency", "EUR"),
    )

    database.add(entry)
    await database.commit()
    await database.refresh(entry)
    return entry


# ── Full Passport Scan ─────────────────────────────────────────


async def full_passport_scan(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_qualification: str,
    source_country: str,
    target_country: str,
    nationality: str,
) -> dict[str, Any]:
    """Execute full passport scan for a target country.

    Pipeline:
        1. Map credential
        2. Compare countries
        3. Assess visa
        4. Analyze market demand
        5. Compute passport score

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        source_qualification: Qualification to map.
        source_country: Country of origin.
        target_country: Target destination.
        nationality: User's nationality.

    Returns:
        Dict with all analysis results and passport score.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    credential = await map_credential(
        database,
        user_id=user_id,
        source_qualification=source_qualification,
        source_country=source_country,
        target_country=target_country,
    )

    comparison = await compare_countries(
        database,
        user_id=user_id,
        source_country=source_country,
        target_country=target_country,
    )

    visa = await assess_visa(
        database,
        user_id=user_id,
        nationality=nationality,
        target_country=target_country,
    )

    market = await get_market_demand(
        database,
        user_id=user_id,
        country=target_country,
    )

    score_data = CareerPassportAnalyzer.compute_passport_score(
        credential_confidence=credential.confidence_score,
        visa_eligibility=visa.eligibility_score,
        demand_level=comparison.market_demand_level,
        purchasing_power_delta=comparison.purchasing_power_delta,
    )
    score_data["target_country"] = target_country

    return {
        "credential_mapping": credential,
        "country_comparison": comparison,
        "visa_assessment": visa,
        "market_demand": market,
        "passport_score": score_data,
    }


# ── Dashboard ──────────────────────────────────────────────────


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get aggregated Career Passport dashboard.

    Returns all credential mappings, comparisons, visa assessments,
    market demand entries, preferences, and passport scores.

    Args:
        database: Async database session.
        user_id: Current user's UUID.

    Returns:
        Dict with all passport data for dashboard display.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return {
            "credential_mappings": [],
            "country_comparisons": [],
            "visa_assessments": [],
            "market_demand": [],
            "preferences": None,
            "passport_scores": [],
        }

    # Fetch all records
    mappings_result = await database.execute(
        select(CredentialMapping)
        .where(CredentialMapping.career_dna_id == career_dna.id)
        .order_by(CredentialMapping.created_at.desc())
    )
    mappings = list(mappings_result.scalars().all())

    comparisons_result = await database.execute(
        select(CountryComparison)
        .where(CountryComparison.career_dna_id == career_dna.id)
        .order_by(CountryComparison.created_at.desc())
    )
    comparisons = list(comparisons_result.scalars().all())

    visas_result = await database.execute(
        select(VisaAssessment)
        .where(VisaAssessment.career_dna_id == career_dna.id)
        .order_by(VisaAssessment.created_at.desc())
    )
    visas = list(visas_result.scalars().all())

    demand_result = await database.execute(
        select(MarketDemandEntry)
        .where(MarketDemandEntry.career_dna_id == career_dna.id)
        .order_by(MarketDemandEntry.created_at.desc())
    )
    demand = list(demand_result.scalars().all())

    pref_result = await database.execute(
        select(CareerPassportPreference)
        .where(CareerPassportPreference.career_dna_id == career_dna.id)
    )
    pref = pref_result.scalar_one_or_none()

    # Compute passport scores per unique target country
    scores: list[dict[str, Any]] = []
    target_countries: set[str] = set()
    for comp in comparisons:
        if comp.target_country not in target_countries:
            target_countries.add(comp.target_country)
            # Find matching credential and visa
            cred_conf = 0.5
            visa_elig = 0.5
            for mapping in mappings:
                if mapping.target_country == comp.target_country:
                    cred_conf = mapping.confidence_score
                    break
            for visa in visas:
                if visa.target_country == comp.target_country:
                    visa_elig = visa.eligibility_score
                    break

            score = CareerPassportAnalyzer.compute_passport_score(
                credential_confidence=cred_conf,
                visa_eligibility=visa_elig,
                demand_level=comp.market_demand_level,
                purchasing_power_delta=comp.purchasing_power_delta,
            )
            score["target_country"] = comp.target_country
            scores.append(score)

    return {
        "credential_mappings": mappings,
        "country_comparisons": comparisons,
        "visa_assessments": visas,
        "market_demand": demand,
        "preferences": pref,
        "passport_scores": scores,
    }


# ── Preferences ────────────────────────────────────────────────


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> CareerPassportPreference | None:
    """Get Career Passport preferences."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(CareerPassportPreference)
        .where(CareerPassportPreference.career_dna_id == career_dna.id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: CareerPassportPreferenceUpdate,
) -> CareerPassportPreference:
    """Update or create Career Passport preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        update_data: Preference update payload.

    Returns:
        Updated or created preference record.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await database.execute(
        select(CareerPassportPreference)
        .where(CareerPassportPreference.career_dna_id == career_dna.id)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        pref = CareerPassportPreference(
            career_dna_id=career_dna.id,
            user_id=user_id,
        )
        database.add(pref)

    if update_data.preferred_countries is not None:
        pref.preferred_countries = {"countries": update_data.preferred_countries}
    if update_data.nationality is not None:
        pref.nationality = update_data.nationality
    if update_data.include_visa_info is not None:
        pref.include_visa_info = update_data.include_visa_info
    if update_data.include_col_comparison is not None:
        pref.include_col_comparison = update_data.include_col_comparison
    if update_data.include_market_demand is not None:
        pref.include_market_demand = update_data.include_market_demand

    await database.commit()
    await database.refresh(pref)
    return pref


# ── Single Record Retrieval ────────────────────────────────────


async def get_credential_mapping(
    database: AsyncSession,
    *,
    mapping_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CredentialMapping | None:
    """Get a specific credential mapping by ID."""
    result = await database.execute(
        select(CredentialMapping)
        .where(
            CredentialMapping.id == mapping_id,
            CredentialMapping.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_credential_mapping(
    database: AsyncSession,
    *,
    mapping_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a credential mapping by ID.

    Returns:
        True if deleted, False if not found.
    """
    result = await database.execute(
        select(CredentialMapping)
        .where(
            CredentialMapping.id == mapping_id,
            CredentialMapping.user_id == user_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        return False

    await database.delete(mapping)
    await database.commit()
    return True


async def get_market_demand_by_country(
    database: AsyncSession,
    *,
    country: str,
    user_id: uuid.UUID,
) -> list[MarketDemandEntry]:
    """Get all market demand entries for a country."""
    result = await database.execute(
        select(MarketDemandEntry)
        .where(
            MarketDemandEntry.user_id == user_id,
            MarketDemandEntry.country == country,
        )
        .order_by(MarketDemandEntry.created_at.desc())
    )
    return list(result.scalars().all())
