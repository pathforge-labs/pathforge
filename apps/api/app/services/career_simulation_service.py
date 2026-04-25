"""
PathForge — Career Simulation Engine™ Service
================================================
Pipeline orchestration for the Career Simulation Engine.

Coordinates AI analyzer calls with database persistence,
Career DNA context extraction, and response composition.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer
from app.models.career_dna import CareerDNA
from app.models.career_simulation import (
    CareerSimulation,
    SimulationInput,
    SimulationOutcome,
    SimulationPreference,
    SimulationRecommendation,
)
from app.schemas.career_simulation import SimulationPreferenceUpdateRequest

logger = logging.getLogger(__name__)


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_genome(
    database: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with eager-loaded skill genome."""
    result = await database.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(selectinload(CareerDNA.skill_genome))
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


def _get_skill_names(career_dna: CareerDNA) -> list[str]:
    """Extract skill names from Career DNA genome."""
    if not career_dna.skill_genome:
        return []
    return [entry.skill_name for entry in career_dna.skill_genome]


def _get_years_experience(career_dna: CareerDNA) -> int:
    """Estimate years of experience from Career DNA context."""
    if hasattr(career_dna, "experience_blueprint") and career_dna.experience_blueprint:
        return max(1, int(career_dna.experience_blueprint.total_years))
    return 3  # Default assumption


def _build_scenario_params(
    scenario_type: str,
    **kwargs: Any,
) -> str:
    """Format scenario parameters for prompt consumption."""
    params_lines: list[str] = [f"Scenario type: {scenario_type}"]
    for key, value in kwargs.items():
        if value is not None:
            label = key.replace("_", " ").title()
            params_lines.append(f"- {label}: {value}")
    return "\n".join(params_lines)


def _store_inputs(
    simulation: CareerSimulation,
    params: dict[str, Any],
) -> list[SimulationInput]:
    """Create SimulationInput records from parameter dict."""
    inputs: list[SimulationInput] = []
    for key, value in params.items():
        if value is not None:
            param_input = SimulationInput(
                simulation_id=simulation.id,
                parameter_name=key,
                parameter_value=str(value),
                parameter_type=type(value).__name__,
            )
            inputs.append(param_input)
    return inputs


def _store_outcomes(
    simulation: CareerSimulation,
    outcomes_data: list[dict[str, Any]],
) -> list[SimulationOutcome]:
    """Create SimulationOutcome records from projected data."""
    outcomes: list[SimulationOutcome] = []
    for outcome_data in outcomes_data:
        outcome = SimulationOutcome(
            simulation_id=simulation.id,
            dimension=outcome_data.get("dimension", "unknown"),
            current_value=outcome_data.get("current_value", 0.0),
            projected_value=outcome_data.get("projected_value", 0.0),
            delta=outcome_data.get("delta", 0.0),
            unit=outcome_data.get("unit"),
            reasoning=outcome_data.get("reasoning"),
        )
        outcomes.append(outcome)
    return outcomes


def _store_recommendations(
    simulation: CareerSimulation,
    rec_data: list[dict[str, Any]],
) -> list[SimulationRecommendation]:
    """Create SimulationRecommendation records."""
    recommendations: list[SimulationRecommendation] = []
    for rec in rec_data:
        recommendation = SimulationRecommendation(
            simulation_id=simulation.id,
            priority=rec.get("priority", "medium"),
            title=rec.get("title", "Untitled"),
            description=rec.get("description"),
            estimated_weeks=rec.get("estimated_weeks"),
            order_index=rec.get("order_index", 0),
        )
        recommendations.append(recommendation)
    return recommendations


def _default_analysis(scenario_type: str) -> dict[str, Any]:
    """Safe fallback analysis when LLM fails."""
    return {
        "confidence_score": 0.5,
        "feasibility_rating": 50.0,
        "salary_impact_percent": 0.0,
        "estimated_months": 6,
        "reasoning": (
            "Analysis based on general career transition patterns. "
            "Detailed AI analysis was unavailable."
        ),
        "factors": {
            "note": f"Default {scenario_type} analysis — LLM fallback",
        },
    }


# ── Core Simulation Pipeline ──────────────────────────────────


async def _run_simulation_pipeline(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    scenario_type: str,
    scenario_params: dict[str, Any],
) -> CareerSimulation:
    """
    Core simulation pipeline: analyze → project → recommend → persist.

    Shared by all 5 scenario type endpoints.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        scenario_type: One of the 5 scenario types.
        scenario_params: Scenario-specific parameters.

    Returns:
        Persisted CareerSimulation with all children loaded.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found. Build your profile first.")

    current_role = career_dna.primary_role or "Professional"
    current_seniority = career_dna.seniority_level or "Mid"
    current_industry = career_dna.primary_industry or "Technology"
    current_location = career_dna.location or "Remote"
    skills_text = _format_skills_for_prompt(career_dna)
    years_exp = _get_years_experience(career_dna)

    params_text = _build_scenario_params(scenario_type, **scenario_params)

    # Step 1: Analyze scenario
    analysis = await CareerSimulationAnalyzer.analyze_scenario(
        scenario_type=scenario_type,
        current_role=current_role,
        current_seniority=current_seniority,
        current_industry=current_industry,
        current_location=current_location,
        skills=skills_text,
        years_experience=years_exp,
        scenario_parameters=params_text,
    )
    if not analysis:
        analysis = _default_analysis(scenario_type)

    # Step 2: Project outcomes
    outcomes_data = await CareerSimulationAnalyzer.project_outcomes(
        scenario_type=scenario_type,
        current_role=current_role,
        scenario_parameters=params_text,
        confidence_score=analysis.get("confidence_score", 0.5),
        reasoning=analysis.get("reasoning", ""),
    )

    # Step 3: Generate recommendations
    outcomes_summary = json.dumps(outcomes_data[:4]) if outcomes_data else "[]"
    rec_data = await CareerSimulationAnalyzer.generate_recommendations(
        scenario_type=scenario_type,
        current_role=current_role,
        scenario_parameters=params_text,
        confidence_score=analysis.get("confidence_score", 0.5),
        reasoning=analysis.get("reasoning", ""),
        outcomes_summary=outcomes_summary,
    )

    # Step 4: Persist everything
    simulation = CareerSimulation(
        career_dna_id=career_dna.id,
        scenario_type=scenario_type,
        confidence_score=analysis.get("confidence_score", 0.5),
        feasibility_rating=analysis.get("feasibility_rating", 50.0),
        roi_score=None,  # Computed post-hoc from outcomes
        salary_impact_percent=analysis.get("salary_impact_percent"),
        estimated_months=analysis.get("estimated_months"),
        reasoning=analysis.get("reasoning"),
        factors=analysis.get("factors"),
    )
    database.add(simulation)
    await database.flush()  # Get simulation.id

    # Store inputs
    input_records = _store_inputs(simulation, scenario_params)
    for record in input_records:
        database.add(record)

    # Store outcomes
    outcome_records = _store_outcomes(simulation, outcomes_data)
    for outcome_record in outcome_records:
        database.add(outcome_record)

    # Store recommendations
    rec_records = _store_recommendations(simulation, rec_data)
    for rec_record in rec_records:
        database.add(rec_record)

    await database.commit()

    # Reload with relationships
    result = await database.execute(
        select(CareerSimulation)
        .where(CareerSimulation.id == simulation.id)
        .options(
            selectinload(CareerSimulation.inputs),
            selectinload(CareerSimulation.outcomes),
            selectinload(CareerSimulation.recommendations),
        )
    )
    return result.scalar_one()


# ── Public Service Methods ─────────────────────────────────────


async def simulate_role_transition(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_role: str,
    target_industry: str | None = None,
    target_location: str | None = None,
) -> CareerSimulation:
    """Run role transition simulation pipeline."""
    return await _run_simulation_pipeline(
        database,
        user_id=user_id,
        scenario_type="role_transition",
        scenario_params={
            "target_role": target_role,
            "target_industry": target_industry,
            "target_location": target_location,
        },
    )


async def simulate_geo_move(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_location: str,
    keep_role: bool = True,
    target_role: str | None = None,
) -> CareerSimulation:
    """Run geographic move simulation pipeline."""
    return await _run_simulation_pipeline(
        database,
        user_id=user_id,
        scenario_type="geo_move",
        scenario_params={
            "target_location": target_location,
            "keep_role": keep_role,
            "target_role": target_role,
        },
    )


async def simulate_skill_investment(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    skills: list[str],
    target_role: str | None = None,
) -> CareerSimulation:
    """Run skill investment simulation pipeline."""
    return await _run_simulation_pipeline(
        database,
        user_id=user_id,
        scenario_type="skill_investment",
        scenario_params={
            "skills": ", ".join(skills),
            "target_role": target_role,
        },
    )


async def simulate_industry_pivot(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_industry: str,
    target_role: str | None = None,
) -> CareerSimulation:
    """Run industry pivot simulation pipeline."""
    return await _run_simulation_pipeline(
        database,
        user_id=user_id,
        scenario_type="industry_pivot",
        scenario_params={
            "target_industry": target_industry,
            "target_role": target_role,
        },
    )


async def simulate_seniority_jump(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_seniority: str,
    target_role: str | None = None,
) -> CareerSimulation:
    """Run seniority jump simulation pipeline."""
    return await _run_simulation_pipeline(
        database,
        user_id=user_id,
        scenario_type="seniority_jump",
        scenario_params={
            "target_seniority": target_seniority,
            "target_role": target_role,
        },
    )


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Get all saved simulations + preferences for dashboard view."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return {
            "simulations": [],
            "preferences": None,
            "total_simulations": 0,
            "scenario_type_counts": {},
        }

    # Total count
    base_query = (
        select(CareerSimulation)
        .where(CareerSimulation.career_dna_id == career_dna.id)
    )
    total = await database.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    # Paginated fetch
    simulations = (
        (
            await database.execute(
                base_query
                .order_by(CareerSimulation.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )

    preferences = (
        await database.execute(
            select(SimulationPreference)
            .where(SimulationPreference.career_dna_id == career_dna.id)
        )
    ).scalar_one_or_none()

    # Count simulations per scenario type (across all, not just page)
    all_sims = (
        (
            await database.execute(
                select(CareerSimulation.scenario_type)
                .where(CareerSimulation.career_dna_id == career_dna.id)
            )
        )
        .scalars()
        .all()
    )
    type_counts: dict[str, int] = {}
    for scenario in all_sims:
        type_counts[scenario] = type_counts.get(scenario, 0) + 1

    return {
        "simulations": list(simulations),
        "preferences": preferences,
        "total_simulations": total,
        "scenario_type_counts": type_counts,
    }


async def get_simulation(
    database: AsyncSession,
    *,
    simulation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CareerSimulation | None:
    """Get a specific simulation by ID with relationships."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(CareerSimulation)
        .where(
            CareerSimulation.id == simulation_id,
            CareerSimulation.career_dna_id == career_dna.id,
        )
        .options(
            selectinload(CareerSimulation.inputs),
            selectinload(CareerSimulation.outcomes),
            selectinload(CareerSimulation.recommendations),
        )
    )
    return result.scalar_one_or_none()


async def list_simulations(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[CareerSimulation], int]:
    """List all simulations for a user with pagination."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return [], 0

    base_query = (
        select(CareerSimulation)
        .where(CareerSimulation.career_dna_id == career_dna.id)
    )

    # Total count
    total = await database.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    # Paginated fetch
    result = await database.execute(
        base_query
        .order_by(CareerSimulation.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(result.scalars().all()), total


async def delete_simulation(
    database: AsyncSession,
    *,
    simulation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a saved simulation and all children."""
    simulation = await get_simulation(
        database, simulation_id=simulation_id, user_id=user_id,
    )
    if not simulation:
        return False

    await database.delete(simulation)
    await database.commit()
    return True


async def compare_simulations(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    simulation_ids: list[uuid.UUID],
) -> dict[str, Any]:
    """Compare multiple simulations side-by-side."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    simulations: list[CareerSimulation] = []
    for sim_id in simulation_ids:
        sim = await get_simulation(
            database, simulation_id=sim_id, user_id=user_id,
        )
        if sim:
            simulations.append(sim)

    if len(simulations) < 2:
        raise ValueError("At least 2 valid simulations required for comparison.")

    # Build JSON for LLM comparison
    scenarios_summary = [
        {
            "id": str(sim.id),
            "scenario_type": sim.scenario_type,
            "confidence_score": sim.confidence_score,
            "feasibility_rating": sim.feasibility_rating,
            "salary_impact_percent": sim.salary_impact_percent,
            "estimated_months": sim.estimated_months,
        }
        for sim in simulations
    ]

    comparison = await CareerSimulationAnalyzer.compare_scenarios(
        current_role=career_dna.primary_role or "Professional",
        current_seniority=career_dna.seniority_level or "Mid",
        current_industry=career_dna.primary_industry or "Technology",
        scenarios_json=json.dumps(scenarios_summary, indent=2),
    )

    return {
        "simulations": simulations,
        "ranking": comparison.get("ranking", []),
        "trade_off_analysis": comparison.get("trade_off_analysis"),
    }


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> SimulationPreference | None:
    """Get simulation preferences for a user."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(SimulationPreference)
        .where(SimulationPreference.career_dna_id == career_dna.id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: SimulationPreferenceUpdateRequest,
) -> SimulationPreference:
    """Update or create simulation preferences."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    result = await database.execute(
        select(SimulationPreference)
        .where(SimulationPreference.career_dna_id == career_dna.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        preference = SimulationPreference(
            career_dna_id=career_dna.id,
            user_id=user_id,
        )
        database.add(preference)

    # Apply partial updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(preference, field, value)

    await database.commit()
    await database.refresh(preference)
    return preference
