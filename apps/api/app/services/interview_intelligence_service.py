"""
PathForge — Interview Intelligence™ Service
=============================================
Pipeline orchestration for the Interview Intelligence Engine.

Coordinates AI analyzer calls with database persistence,
Career DNA context extraction, Salary Intelligence integration,
and response composition.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.interview_intelligence_analyzer import InterviewIntelligenceAnalyzer
from app.models.career_dna import CareerDNA
from app.models.interview_intelligence import (
    CompanyInsight,
    InterviewPreference,
    InterviewPrep,
    InterviewQuestion,
    PrepDepth,
    PrepStatus,
    STARExample,
)
from app.models.salary_intelligence import SalaryEstimate
from app.schemas.interview_intelligence import (
    InterviewPreferenceUpdateRequest,
)

logger = logging.getLogger(__name__)


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_context(
    database: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with eager-loaded skill genome and experience."""
    result = await database.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(
            selectinload(CareerDNA.skill_genome),
            selectinload(CareerDNA.experience_blueprint),
            selectinload(CareerDNA.growth_vector),
            selectinload(CareerDNA.values_profile),
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
        blueprints = career_dna.experience_blueprint
        if isinstance(blueprints, list) and blueprints:
            return max(1, len(blueprints) * 2)
    return 3  # Default assumption


def _get_career_summary(career_dna: CareerDNA) -> str:
    """Extract a career summary from Career DNA."""
    parts: list[str] = []
    if career_dna.primary_role:
        parts.append(f"Role: {career_dna.primary_role}")
    if career_dna.seniority_level:
        parts.append(f"Seniority: {career_dna.seniority_level}")
    if career_dna.primary_industry:
        parts.append(f"Industry: {career_dna.primary_industry}")
    return ", ".join(parts) if parts else "No career summary available"


def _get_experience_text(career_dna: CareerDNA) -> str:
    """Format experience blueprint for STAR prompt."""
    if not career_dna.experience_blueprint:
        return "No experience data"
    blueprints = career_dna.experience_blueprint
    if isinstance(blueprints, list):
        lines: list[str] = []
        for bp in blueprints[:5]:
            role = getattr(bp, "role_title", "Unknown role")
            company = getattr(bp, "company_context", "Unknown")
            lines.append(f"- {role} at {company}")
        return "\n".join(lines)
    return "No experience data"


def _get_growth_text(career_dna: CareerDNA) -> str:
    """Format growth vector for STAR prompt."""
    if not career_dna.growth_vector:
        return "No growth data"
    vectors = career_dna.growth_vector
    if isinstance(vectors, list):
        lines: list[str] = []
        for gv in vectors[:5]:
            direction = getattr(gv, "direction", "unknown")
            target = getattr(gv, "target_role", "unknown")
            lines.append(f"- Direction: {direction}, Target: {target}")
        return "\n".join(lines)
    return "No growth data"


def _get_values_text(career_dna: CareerDNA) -> str:
    """Format values profile for STAR prompt."""
    if not career_dna.values_profile:
        return "No values data"
    values = career_dna.values_profile
    if isinstance(values, list):
        lines: list[str] = []
        for vp in values[:5]:
            name = getattr(vp, "value_name", "unknown")
            priority = getattr(vp, "priority_rank", 0)
            lines.append(f"- {name} (priority: {priority})")
        return "\n".join(lines)
    return "No values data"


def _store_insights(
    prep: InterviewPrep,
    insights_data: list[dict[str, Any]],
) -> list[CompanyInsight]:
    """Create CompanyInsight records from analysis data."""
    insights: list[CompanyInsight] = []
    for insight_data in insights_data:
        insight = CompanyInsight(
            interview_prep_id=prep.id,
            insight_type=insight_data.get("insight_type", "culture"),
            title=insight_data.get("title", "Untitled insight"),
            content=insight_data.get("content"),
            summary=insight_data.get("summary"),
            source=insight_data.get("source"),
            confidence=insight_data.get("confidence", 0.5),
        )
        insights.append(insight)
    return insights


def _store_questions(
    prep: InterviewPrep,
    questions_data: list[dict[str, Any]],
) -> list[InterviewQuestion]:
    """Create InterviewQuestion records from generated data."""
    questions: list[InterviewQuestion] = []
    for q_data in questions_data:
        question = InterviewQuestion(
            interview_prep_id=prep.id,
            category=q_data.get("category", "behavioral"),
            question_text=q_data.get("question_text", ""),
            suggested_answer=q_data.get("suggested_answer"),
            answer_strategy=q_data.get("answer_strategy"),
            frequency_weight=q_data.get("frequency_weight", 0.5),
            difficulty_level=q_data.get("difficulty_level"),
            order_index=q_data.get("order_index", 0),
        )
        questions.append(question)
    return questions


def _store_star_examples(
    prep: InterviewPrep,
    examples_data: list[dict[str, Any]],
    question_map: dict[int, str] | None = None,
) -> list[STARExample]:
    """Create STARExample records from generated data."""
    examples: list[STARExample] = []
    for example_data in examples_data:
        example = STARExample(
            interview_prep_id=prep.id,
            question_id=None,  # Linked post-hoc if question_map provided
            situation=example_data.get("situation", ""),
            task=example_data.get("task", ""),
            action=example_data.get("action", ""),
            result=example_data.get("result", ""),
            career_dna_dimension=example_data.get("career_dna_dimension"),
            source_experience=example_data.get("source_experience"),
            relevance_score=example_data.get("relevance_score", 0.5),
            order_index=example_data.get("order_index", 0),
        )
        examples.append(example)
    return examples


def _default_company_analysis(company_name: str, target_role: str) -> dict[str, Any]:
    """Safe fallback analysis when LLM fails."""
    return {
        "company_brief": f"Analysis for {company_name} ({target_role}).",
        "interview_format": "Standard multi-round interview process.",
        "confidence_score": 0.3,
        "culture_alignment_score": 0.5,
        "insights": [],
    }


# ── Core Interview Prep Pipeline ──────────────────────────────


async def create_interview_prep(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    company_name: str,
    target_role: str,
    prep_depth: str | None = None,
) -> InterviewPrep:
    """
    Create a full interview preparation session.

    Pipeline: analyze company → generate questions → generate STARs → persist.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        company_name: Target company for interview prep.
        target_role: Target role at the company.
        prep_depth: Preparation depth (quick/standard/comprehensive).

    Returns:
        Persisted InterviewPrep with all children loaded.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found. Build your profile first.")

    depth = prep_depth or PrepDepth.STANDARD.value
    current_role = career_dna.primary_role or "Professional"
    current_seniority = career_dna.seniority_level or "Mid"
    current_industry = career_dna.primary_industry or "Technology"
    skills_text = _format_skills_for_prompt(career_dna)
    years_exp = _get_years_experience(career_dna)

    # Step 1: Analyze company
    analysis = await InterviewIntelligenceAnalyzer.analyze_company(
        company_name=company_name,
        target_role=target_role,
        prep_depth=depth,
        current_role=current_role,
        current_seniority=current_seniority,
        current_industry=current_industry,
        skills=skills_text,
        years_experience=years_exp,
    )
    if not analysis:
        analysis = _default_company_analysis(company_name, target_role)

    # Step 2: Generate questions
    questions_data = await InterviewIntelligenceAnalyzer.generate_questions(
        company_name=company_name,
        target_role=target_role,
        interview_format=analysis.get("interview_format", ""),
        company_brief=analysis.get("company_brief", ""),
        current_role=current_role,
        skills=skills_text,
        years_experience=years_exp,
        max_questions=15 if depth == PrepDepth.QUICK.value else 25,
    )

    # Step 3: Generate STAR examples
    star_data = await InterviewIntelligenceAnalyzer.generate_star_examples(
        company_name=company_name,
        target_role=target_role,
        current_role=current_role,
        career_summary=_get_career_summary(career_dna),
        skills=skills_text,
        experience_blueprint=_get_experience_text(career_dna),
        growth_trajectory=_get_growth_text(career_dna),
        values_profile=_get_values_text(career_dna),
        max_examples=5 if depth == PrepDepth.QUICK.value else 10,
    )

    # Step 4: Persist everything
    prep = InterviewPrep(
        career_dna_id=career_dna.id,
        user_id=user_id,
        company_name=company_name,
        target_role=target_role,
        status=PrepStatus.COMPLETED.value,
        prep_depth=depth,
        confidence_score=analysis.get("confidence_score", 0.3),
        culture_alignment_score=analysis.get("culture_alignment_score"),
        interview_format=analysis.get("interview_format"),
        company_brief=analysis.get("company_brief"),
    )
    database.add(prep)
    await database.flush()

    # Store insights
    insight_records = _store_insights(prep, analysis.get("insights", []))
    for record in insight_records:
        database.add(record)

    # Store questions
    question_records = _store_questions(prep, questions_data)
    for question_record in question_records:
        database.add(question_record)

    # Store STAR examples
    star_records = _store_star_examples(prep, star_data)
    for star_record in star_records:
        database.add(star_record)

    await database.commit()

    # Reload with relationships
    return await _load_prep_with_relations(database, prep.id)


# ── Public Service Methods ─────────────────────────────────────


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get all interview preps + preferences for dashboard view."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return {
            "preps": [],
            "preferences": None,
            "total_preps": 0,
            "company_counts": {},
        }

    # Fetch all preps (summary)
    preps_result = await database.execute(
        select(InterviewPrep)
        .where(InterviewPrep.career_dna_id == career_dna.id)
        .order_by(InterviewPrep.created_at.desc())
    )
    preps = list(preps_result.scalars().all())

    # Preferences
    pref_result = await database.execute(
        select(InterviewPreference)
        .where(InterviewPreference.career_dna_id == career_dna.id)
    )
    preferences = pref_result.scalar_one_or_none()

    # Company counts
    company_counts: dict[str, int] = {}
    for prep in preps:
        company_counts[prep.company_name] = (
            company_counts.get(prep.company_name, 0) + 1
        )

    return {
        "preps": preps,
        "preferences": preferences,
        "total_preps": len(preps),
        "company_counts": company_counts,
    }


async def get_interview_prep(
    database: AsyncSession,
    *,
    prep_id: uuid.UUID,
    user_id: uuid.UUID,
) -> InterviewPrep | None:
    """Get a specific interview prep by ID with all relationships."""
    result = await database.execute(
        select(InterviewPrep)
        .where(
            InterviewPrep.id == prep_id,
            InterviewPrep.user_id == user_id,
        )
        .options(
            selectinload(InterviewPrep.insights),
            selectinload(InterviewPrep.questions)
            .selectinload(InterviewQuestion.star_examples),
            selectinload(InterviewPrep.star_examples),
        )
    )
    return result.scalar_one_or_none()


async def generate_questions_for_prep(
    database: AsyncSession,
    *,
    prep_id: uuid.UUID,
    user_id: uuid.UUID,
    category_filter: str | None = None,
    max_questions: int = 15,
) -> InterviewPrep | None:
    """Generate additional questions for an existing prep."""
    prep = await get_interview_prep(database, prep_id=prep_id, user_id=user_id)
    if not prep:
        return None

    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    questions_data = await InterviewIntelligenceAnalyzer.generate_questions(
        company_name=prep.company_name,
        target_role=prep.target_role,
        interview_format=prep.interview_format or "",
        company_brief=prep.company_brief or "",
        current_role=career_dna.primary_role or "Professional",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        category_filter=category_filter,
        max_questions=max_questions,
    )

    question_records = _store_questions(prep, questions_data)
    for record in question_records:
        database.add(record)

    await database.commit()
    return await _load_prep_with_relations(database, prep.id)


async def generate_star_examples_for_prep(
    database: AsyncSession,
    *,
    prep_id: uuid.UUID,
    user_id: uuid.UUID,
    max_examples: int = 10,
) -> InterviewPrep | None:
    """Generate additional STAR examples for an existing prep."""
    prep = await get_interview_prep(database, prep_id=prep_id, user_id=user_id)
    if not prep:
        return None

    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    # Build question context from existing questions
    question_context = "No specific questions provided."
    if prep.questions:
        question_lines = [
            f"- [{q.category}] {q.question_text}"
            for q in prep.questions[:10]
        ]
        question_context = "\n".join(question_lines)

    star_data = await InterviewIntelligenceAnalyzer.generate_star_examples(
        company_name=prep.company_name,
        target_role=prep.target_role,
        current_role=career_dna.primary_role or "Professional",
        career_summary=_get_career_summary(career_dna),
        skills=_format_skills_for_prompt(career_dna),
        experience_blueprint=_get_experience_text(career_dna),
        growth_trajectory=_get_growth_text(career_dna),
        values_profile=_get_values_text(career_dna),
        question_context=question_context,
        max_examples=max_examples,
    )

    star_records = _store_star_examples(prep, star_data)
    for record in star_records:
        database.add(record)

    await database.commit()
    return await _load_prep_with_relations(database, prep.id)


async def generate_negotiation_script(
    database: AsyncSession,
    *,
    prep_id: uuid.UUID,
    user_id: uuid.UUID,
    target_salary: float | None = None,
    currency: str = "EUR",
) -> dict[str, Any]:
    """Generate salary negotiation scripts for an interview prep."""
    prep = await get_interview_prep(database, prep_id=prep_id, user_id=user_id)
    if not prep:
        raise ValueError("Interview prep not found.")

    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    # Fetch latest Salary Intelligence estimate for this user
    salary_estimates: list[dict[str, Any]] = []
    estimate_result = await database.execute(
        select(SalaryEstimate)
        .where(SalaryEstimate.career_dna_id == career_dna.id)
        .order_by(desc(SalaryEstimate.computed_at))
        .limit(1)
    )
    latest_estimate = estimate_result.scalar_one_or_none()
    if latest_estimate:
        salary_estimates.append({
            "role_title": latest_estimate.role_title,
            "estimated_min": latest_estimate.estimated_min,
            "estimated_max": latest_estimate.estimated_max,
            "estimated_median": latest_estimate.estimated_median,
            "currency": latest_estimate.currency,
            "confidence": latest_estimate.confidence,
            "seniority_level": latest_estimate.seniority_level,
            "location": latest_estimate.location,
        })

    salary_data = InterviewIntelligenceAnalyzer.merge_salary_data(
        salary_estimates=salary_estimates,
        target_role=prep.target_role,
        currency=currency,
    )

    script_data = await InterviewIntelligenceAnalyzer.generate_negotiation_script(
        company_name=prep.company_name,
        target_role=prep.target_role,
        current_role=career_dna.primary_role or "Professional",
        current_seniority=career_dna.seniority_level or "Mid",
        skills=_format_skills_for_prompt(career_dna),
        years_experience=_get_years_experience(career_dna),
        salary_data=salary_data,
        target_salary=target_salary,
        currency=currency,
    )

    # Attach prep context to response
    script_data["interview_prep_id"] = str(prep.id)
    script_data["company_name"] = prep.company_name
    script_data["target_role"] = prep.target_role
    return script_data


async def delete_interview_prep(
    database: AsyncSession,
    *,
    prep_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a saved interview prep and all children."""
    prep = await get_interview_prep(database, prep_id=prep_id, user_id=user_id)
    if not prep:
        return False

    await database.delete(prep)
    await database.commit()
    return True


async def compare_interview_preps(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    prep_ids: list[uuid.UUID],
) -> dict[str, Any]:
    """Compare multiple interview preps side-by-side."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    preps: list[InterviewPrep] = []
    for pid in prep_ids:
        prep = await get_interview_prep(database, prep_id=pid, user_id=user_id)
        if prep:
            preps.append(prep)

    if len(preps) < 2:
        raise ValueError("At least 2 valid interview preps required for comparison.")

    preps_summary = [
        {
            "id": str(prep.id),
            "company_name": prep.company_name,
            "target_role": prep.target_role,
            "confidence_score": prep.confidence_score,
            "culture_alignment_score": prep.culture_alignment_score,
            "questions_count": len(prep.questions) if prep.questions else 0,
            "star_examples_count": len(prep.star_examples) if prep.star_examples else 0,
        }
        for prep in preps
    ]

    comparison = await InterviewIntelligenceAnalyzer.compare_preps(
        current_role=career_dna.primary_role or "Professional",
        current_seniority=career_dna.seniority_level or "Mid",
        current_industry=career_dna.primary_industry or "Technology",
        preps_json=json.dumps(preps_summary, indent=2),
    )

    return {
        "preps": preps,
        "ranking": comparison.get("ranking", []),
        "comparison_summary": comparison.get("comparison_summary"),
    }


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> InterviewPreference | None:
    """Get interview preferences for a user."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(InterviewPreference)
        .where(InterviewPreference.career_dna_id == career_dna.id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: InterviewPreferenceUpdateRequest,
) -> InterviewPreference:
    """Update or create interview preferences."""
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    result = await database.execute(
        select(InterviewPreference)
        .where(InterviewPreference.career_dna_id == career_dna.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        preference = InterviewPreference(
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


# ── Private Reload Helper ──────────────────────────────────────


async def _load_prep_with_relations(
    database: AsyncSession,
    prep_id: uuid.UUID,
) -> InterviewPrep:
    """Reload an InterviewPrep with all eager-loaded relationships."""
    result = await database.execute(
        select(InterviewPrep)
        .where(InterviewPrep.id == prep_id)
        .options(
            selectinload(InterviewPrep.insights),
            selectinload(InterviewPrep.questions)
            .selectinload(InterviewQuestion.star_examples),
            selectinload(InterviewPrep.star_examples),
        )
    )
    return result.scalar_one()
