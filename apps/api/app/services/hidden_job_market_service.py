"""
PathForge — Hidden Job Market Detector™ Service
=================================================
Pipeline orchestration for the Hidden Job Market Detector.

Coordinates AI analyzer calls with database persistence,
Career DNA context extraction, and response composition.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer
from app.models.career_dna import CareerDNA
from app.models.hidden_job_market import (
    CompanySignal,
    HiddenJobMarketPreference,
    HiddenOpportunity,
    OutreachTemplate,
    SignalMatchResult,
    SignalStatus,
)
from app.schemas.hidden_job_market import (
    DismissSignalRequest,
    GenerateOutreachRequest,
    HiddenJobMarketPreferenceUpdateRequest,
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
    if hasattr(career_dna, "experience_blueprint") and career_dna.experience_blueprint:
        blueprint = career_dna.experience_blueprint
        if hasattr(blueprint, "total_years"):
            return max(1, int(blueprint.total_years))
    return 3  # Default assumption


def _store_match_result(
    signal: CompanySignal,
    match_data: dict[str, Any],
) -> SignalMatchResult:
    """Create a SignalMatchResult record from match analysis."""
    return SignalMatchResult(
        signal_id=signal.id,
        match_score=match_data.get("match_score", 0.0),
        skill_overlap=match_data.get("skill_overlap", 0.0),
        role_relevance=match_data.get("role_relevance", 0.0),
        explanation=match_data.get("explanation"),
        matched_skills=match_data.get("matched_skills"),
        relevance_reasoning=match_data.get("relevance_reasoning"),
    )


def _store_outreach(
    signal: CompanySignal,
    outreach_data: dict[str, Any],
    template_type: str,
    tone: str,
) -> OutreachTemplate:
    """Create an OutreachTemplate record from generated data."""
    return OutreachTemplate(
        signal_id=signal.id,
        template_type=template_type,
        tone=tone,
        subject_line=outreach_data.get("subject_line", "Connection opportunity"),
        body=outreach_data.get("body", ""),
        personalization_points=outreach_data.get("personalization_points"),
        confidence=outreach_data.get("confidence", 0.5),
    )


def _store_opportunities(
    signal: CompanySignal,
    opportunities_data: list[dict[str, Any]],
) -> list[HiddenOpportunity]:
    """Create HiddenOpportunity records from surfaced data."""
    opportunities: list[HiddenOpportunity] = []
    for opp_data in opportunities_data:
        opportunity = HiddenOpportunity(
            signal_id=signal.id,
            predicted_role=opp_data.get("predicted_role", "Unknown role"),
            predicted_seniority=opp_data.get("predicted_seniority"),
            predicted_timeline_days=opp_data.get("predicted_timeline_days"),
            probability=opp_data.get("probability", 0.0),
            reasoning=opp_data.get("reasoning"),
            required_skills=opp_data.get("required_skills"),
            salary_range_min=opp_data.get("salary_range_min"),
            salary_range_max=opp_data.get("salary_range_max"),
            currency=opp_data.get("currency", "EUR"),
        )
        opportunities.append(opportunity)
    return opportunities


def _default_signal_analysis(company_name: str) -> dict[str, Any]:
    """Safe fallback when LLM fails."""
    return {
        "signals": [],
        "company_summary": f"Unable to analyze {company_name} at this time.",
    }


# ── Core Scan Pipeline ────────────────────────────────────────


async def scan_company(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    company_name: str,
    industry: str | None = None,
    focus_signal_types: list[str] | None = None,
) -> list[CompanySignal]:
    """Scan a company for growth signals and match to Career DNA.

    Pipeline: analyze signals → match each → persist → return.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        company_name: Target company to scan.
        industry: Industry context.
        focus_signal_types: Optional filter for signal types.

    Returns:
        List of persisted CompanySignal with match results.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found. Build your profile first.")

    current_role = career_dna.primary_role or "Professional"
    current_seniority = career_dna.seniority_level or "Mid"
    skills_text = _format_skills_for_prompt(career_dna)
    years_exp = _get_years_experience(career_dna)

    # Step 1: Detect signals
    analysis = await HiddenJobMarketAnalyzer.analyze_company_signals(
        company_name=company_name,
        industry=industry or career_dna.primary_industry or "Technology",
        current_role=current_role,
        current_seniority=current_seniority,
    )
    if not analysis:
        analysis = _default_signal_analysis(company_name)

    # Filter by focus types if provided
    raw_signals = analysis.get("signals", [])
    if focus_signal_types:
        raw_signals = [
            sig for sig in raw_signals
            if sig.get("signal_type") in focus_signal_types
        ]

    # Step 2: Create signal records and match each
    persisted_signals: list[CompanySignal] = []
    for signal_data in raw_signals:
        expires_days = signal_data.get("expires_in_days", 90)
        expires_at = datetime.now(tz=UTC) + timedelta(days=expires_days)

        confidence = HiddenJobMarketAnalyzer.compute_signal_confidence(
            llm_confidence=signal_data.get("confidence", 0.5),
            signal_strength=signal_data.get("strength", 0.5),
            career_dna_completeness=career_dna.completeness_score,
        )

        signal = CompanySignal(
            career_dna_id=career_dna.id,
            user_id=user_id,
            company_name=company_name,
            signal_type=signal_data.get("signal_type", "funding"),
            title=signal_data.get("title", "Untitled signal"),
            description=signal_data.get("description"),
            strength=signal_data.get("strength", 0.5),
            source=signal_data.get("source"),
            status=SignalStatus.DETECTED.value,
            confidence_score=confidence,
            expires_at=expires_at,
        )
        database.add(signal)
        await database.flush()

        # Match signal to Career DNA
        match_data = await HiddenJobMarketAnalyzer.match_signal_to_career_dna(
            company_name=company_name,
            signal_type=signal_data.get("signal_type", "funding"),
            signal_title=signal_data.get("title", ""),
            signal_description=signal_data.get("description", ""),
            signal_strength=signal_data.get("strength", 0.5),
            primary_role=current_role,
            seniority_level=current_seniority,
            primary_industry=career_dna.primary_industry or "Technology",
            skills=skills_text,
            years_experience=years_exp,
        )

        match_record = _store_match_result(signal, match_data)
        database.add(match_record)

        # Update signal status
        signal.status = SignalStatus.MATCHED.value
        persisted_signals.append(signal)

    await database.commit()

    # Reload with relationships
    loaded_signals: list[CompanySignal] = []
    for sig in persisted_signals:
        loaded = await _load_signal_with_relations(database, sig.id)
        loaded_signals.append(loaded)

    return loaded_signals


# ── Public Service Methods ─────────────────────────────────────


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get all signals + preferences for dashboard view."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return {
            "signals": [],
            "preferences": None,
            "total_signals": 0,
            "active_signals": 0,
            "matched_signals": 0,
            "dismissed_signals": 0,
            "total_opportunities": 0,
        }

    # Fetch all signals (summary)
    signals_result = await database.execute(
        select(CompanySignal)
        .where(CompanySignal.career_dna_id == career_dna.id)
        .order_by(CompanySignal.created_at.desc())
    )
    signals = list(signals_result.scalars().all())

    # Preferences
    pref_result = await database.execute(
        select(HiddenJobMarketPreference)
        .where(HiddenJobMarketPreference.career_dna_id == career_dna.id)
    )
    preferences = pref_result.scalar_one_or_none()

    # Counts
    active_count = sum(
        1 for sig in signals
        if sig.status in (SignalStatus.DETECTED.value, SignalStatus.MATCHED.value)
    )
    matched_count = sum(
        1 for sig in signals if sig.status == SignalStatus.MATCHED.value
    )
    dismissed_count = sum(
        1 for sig in signals if sig.status == SignalStatus.DISMISSED.value
    )

    # Count opportunities across all signals
    opp_result = await database.execute(
        select(HiddenOpportunity)
        .join(CompanySignal)
        .where(CompanySignal.career_dna_id == career_dna.id)
    )
    total_opportunities = len(list(opp_result.scalars().all()))

    return {
        "signals": signals,
        "preferences": preferences,
        "total_signals": len(signals),
        "active_signals": active_count,
        "matched_signals": matched_count,
        "dismissed_signals": dismissed_count,
        "total_opportunities": total_opportunities,
    }


async def get_signal(
    database: AsyncSession,
    *,
    signal_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CompanySignal | None:
    """Get a specific signal by ID with all relationships."""
    result = await database.execute(
        select(CompanySignal)
        .where(
            CompanySignal.id == signal_id,
            CompanySignal.user_id == user_id,
        )
        .options(
            selectinload(CompanySignal.match_results),
            selectinload(CompanySignal.outreach_templates),
            selectinload(CompanySignal.hidden_opportunities),
        )
    )
    return result.scalar_one_or_none()


async def generate_outreach(
    database: AsyncSession,
    *,
    signal_id: uuid.UUID,
    user_id: uuid.UUID,
    request: GenerateOutreachRequest,
) -> CompanySignal | None:
    """Generate outreach template for a specific signal."""
    signal = await get_signal(database, signal_id=signal_id, user_id=user_id)
    if not signal:
        return None

    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    outreach_data = await HiddenJobMarketAnalyzer.generate_outreach(
        company_name=signal.company_name,
        signal_type=signal.signal_type,
        signal_title=signal.title,
        signal_description=signal.description or "",
        primary_role=career_dna.primary_role or "Professional",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        primary_industry=career_dna.primary_industry or "Technology",
        template_type=request.template_type,
        tone=request.tone,
        custom_notes=request.custom_notes,
    )

    outreach_record = _store_outreach(
        signal, outreach_data, request.template_type, request.tone,
    )
    database.add(outreach_record)
    await database.commit()

    return await _load_signal_with_relations(database, signal.id)


async def dismiss_signal(
    database: AsyncSession,
    *,
    signal_id: uuid.UUID,
    user_id: uuid.UUID,
    request: DismissSignalRequest,
) -> CompanySignal | None:
    """Dismiss or action a signal."""
    signal = await get_signal(database, signal_id=signal_id, user_id=user_id)
    if not signal:
        return None

    new_status = (
        SignalStatus.ACTIONED.value
        if request.action_taken == "actioned"
        else SignalStatus.DISMISSED.value
    )
    signal.status = new_status
    await database.commit()
    await database.refresh(signal)
    return signal


async def compare_signals(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    signal_ids: list[uuid.UUID],
) -> dict[str, Any]:
    """Compare multiple signals side-by-side."""
    signals: list[CompanySignal] = []
    for sid in signal_ids:
        signal = await get_signal(database, signal_id=sid, user_id=user_id)
        if signal:
            signals.append(signal)

    if len(signals) < 2:
        raise ValueError("At least 2 valid signals required for comparison.")

    # Build comparison summary
    strongest = max(signals, key=lambda sig: sig.strength)
    summary = (
        f"Compared {len(signals)} signals. Strongest signal: "
        f"'{strongest.title}' from {strongest.company_name} "
        f"(strength: {strongest.strength:.2f})."
    )

    return {
        "signals": signals,
        "comparison_summary": summary,
        "recommended_signal_id": strongest.id,
    }


async def get_opportunity_radar(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get aggregated opportunity landscape."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return {
            "opportunities": [],
            "total_opportunities": 0,
            "top_industries": [],
            "avg_probability": 0.0,
        }

    opp_result = await database.execute(
        select(HiddenOpportunity)
        .join(CompanySignal)
        .where(CompanySignal.career_dna_id == career_dna.id)
        .order_by(HiddenOpportunity.probability.desc())
    )
    opportunities = list(opp_result.scalars().all())

    avg_prob = (
        sum(opp.probability for opp in opportunities) / len(opportunities)
        if opportunities
        else 0.0
    )

    return {
        "opportunities": opportunities,
        "total_opportunities": len(opportunities),
        "top_industries": [],  # Populated from signal company data
        "avg_probability": round(avg_prob, 3),
    }


async def surface_opportunities(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[CompanySignal]:
    """Surface hidden opportunities from existing signals."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    # Get active signals
    signals_result = await database.execute(
        select(CompanySignal)
        .where(
            CompanySignal.career_dna_id == career_dna.id,
            CompanySignal.status.in_([
                SignalStatus.DETECTED.value,
                SignalStatus.MATCHED.value,
            ]),
        )
        .options(selectinload(CompanySignal.match_results))
    )
    signals = list(signals_result.scalars().all())

    if not signals:
        return []

    # Build signal context for LLM
    signal_dicts = [
        {
            "company_name": sig.company_name,
            "signal_type": sig.signal_type,
            "title": sig.title,
            "description": sig.description,
            "strength": sig.strength,
        }
        for sig in signals
    ]

    opp_result = await HiddenJobMarketAnalyzer.surface_opportunities(
        signals=signal_dicts,
        primary_role=career_dna.primary_role or "Professional",
        seniority_level=career_dna.seniority_level or "Mid",
        skills=_format_skills_for_prompt(career_dna),
        primary_industry=career_dna.primary_industry or "Technology",
    )

    # Store opportunities linked to the first signal
    opportunities_data = opp_result.get("opportunities", [])
    if opportunities_data and signals:
        # Link opps to the strongest signal
        best_signal = max(signals, key=lambda sig: sig.strength)
        opp_records = _store_opportunities(best_signal, opportunities_data)
        for record in opp_records:
            database.add(record)
        await database.commit()

    # Reload signals
    loaded: list[CompanySignal] = []
    for sig in signals:
        loaded.append(await _load_signal_with_relations(database, sig.id))
    return loaded


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> HiddenJobMarketPreference | None:
    """Get hidden job market monitoring preferences."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(HiddenJobMarketPreference)
        .where(HiddenJobMarketPreference.career_dna_id == career_dna.id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: HiddenJobMarketPreferenceUpdateRequest,
) -> HiddenJobMarketPreference:
    """Update or create monitoring preferences."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    result = await database.execute(
        select(HiddenJobMarketPreference)
        .where(HiddenJobMarketPreference.career_dna_id == career_dna.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        preference = HiddenJobMarketPreference(
            career_dna_id=career_dna.id,
            user_id=user_id,
        )
        database.add(preference)

    # Apply partial updates
    update_dict = update_data.model_dump(exclude_unset=True)
    # Convert list to JSON-friendly format
    if update_dict.get("enabled_signal_types"):
        update_dict["enabled_signal_types"] = {
            "types": update_dict["enabled_signal_types"]
        }

    for field, value in update_dict.items():
        setattr(preference, field, value)

    await database.commit()
    await database.refresh(preference)
    return preference


# ── Private Reload Helper ──────────────────────────────────────


async def _load_signal_with_relations(
    database: AsyncSession,
    signal_id: uuid.UUID,
) -> CompanySignal:
    """Reload a CompanySignal with all eager-loaded relationships."""
    result = await database.execute(
        select(CompanySignal)
        .where(CompanySignal.id == signal_id)
        .options(
            selectinload(CompanySignal.match_results),
            selectinload(CompanySignal.outreach_templates),
            selectinload(CompanySignal.hidden_opportunities),
        )
    )
    return result.scalar_one()
