"""
PathForge API — Career DNA Routes
=====================================
REST endpoints for Career DNA™ profile management.

10 endpoints covering:
    - Profile CRUD (get, generate, delete)
    - Dimension access (skill genome, experience, growth, values, market)
    - Hidden skill management (list, confirm/reject)
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.career_dna import (
    CareerDNAGenerateRequest,
    CareerDNAResponse,
    CareerDNASummaryResponse,
    ExperienceBlueprintResponse,
    GrowthVectorResponse,
    HiddenSkillConfirmRequest,
    HiddenSkillResponse,
    MarketPositionResponse,
    SkillGenomeResponse,
    ValuesProfileResponse,
)
from app.services.career_dna_service import CareerDNAService

if TYPE_CHECKING:
    from app.models.career_dna import CareerDNA, HiddenSkill, SkillGenomeEntry
    from app.schemas.career_dna import SkillGenomeEntryResponse

router = APIRouter(prefix="/career-dna", tags=["Career DNA™"])


# ── Profile Endpoints ──────────────────────────────────────────


@router.get(
    "",
    response_model=CareerDNAResponse,
    summary="Get full Career DNA profile",
)
async def get_career_dna(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerDNAResponse:
    """Retrieve the full Career DNA profile with all dimensions."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career DNA profile not found. Generate one first.",
        )
    return _build_full_response(career_dna)


@router.get(
    "/summary",
    response_model=CareerDNASummaryResponse,
    summary="Get Career DNA summary",
)
async def get_career_dna_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerDNASummaryResponse:
    """Lightweight summary with completeness indicator."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career DNA profile not found. Generate one first.",
        )
    return CareerDNASummaryResponse(
        id=career_dna.id,
        completeness_score=career_dna.completeness_score,
        last_analysis_at=career_dna.last_analysis_at,
        version=career_dna.version,
        has_skill_genome=bool(career_dna.skill_genome),
        has_experience_blueprint=career_dna.experience_blueprint is not None,
        has_growth_vector=career_dna.growth_vector is not None,
        has_values_profile=career_dna.values_profile is not None,
        has_market_position=career_dna.market_position is not None,
        hidden_skills_count=len(career_dna.hidden_skills),
    )


@router.post(
    "/generate",
    response_model=CareerDNAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or refresh Career DNA profile",
)
@limiter.limit(settings.rate_limit_career_dna)
async def generate_career_dna(
    request: Request,
    payload: CareerDNAGenerateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerDNAResponse:
    """
    Trigger full Career DNA analysis from user's resume data.

    Optionally specify a subset of dimensions to refresh.
    """
    dimensions = payload.dimensions if payload else None
    career_dna = await CareerDNAService.generate_full_profile(
        db, user_id=current_user.id, dimensions=dimensions
    )
    await db.commit()
    return _build_full_response(career_dna)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Career DNA profile (GDPR erasure)",
)
async def delete_career_dna(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete the entire Career DNA profile. GDPR Art. 17 compliant."""
    deleted = await CareerDNAService.delete_profile(
        db, user_id=current_user.id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career DNA profile not found.",
        )
    await db.commit()


# ── Dimension Endpoints ────────────────────────────────────────


@router.get(
    "/skills",
    response_model=SkillGenomeResponse,
    summary="Get skill genome with hidden skills",
)
async def get_skill_genome(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillGenomeResponse:
    """Get skill genome including AI-discovered hidden skills."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career DNA profile not found.",
        )
    return SkillGenomeResponse(
        explicit_skills=[
            _skill_entry_response(entry) for entry in career_dna.skill_genome
        ],
        hidden_skills=[
            _hidden_skill_response(skill) for skill in career_dna.hidden_skills
        ],
        total_skills=len(career_dna.skill_genome) + len(career_dna.hidden_skills),
    )


@router.get(
    "/experience",
    response_model=ExperienceBlueprintResponse,
    summary="Get experience blueprint",
)
async def get_experience_blueprint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExperienceBlueprintResponse:
    """Get analyzed experience pattern."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None or career_dna.experience_blueprint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience blueprint not found.",
        )
    return ExperienceBlueprintResponse.model_validate(
        career_dna.experience_blueprint
    )


@router.get(
    "/growth",
    response_model=GrowthVectorResponse,
    summary="Get growth vector projection",
)
async def get_growth_vector(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GrowthVectorResponse:
    """Get career trajectory projection with reasoning."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None or career_dna.growth_vector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Growth vector not found.",
        )
    return GrowthVectorResponse.model_validate(career_dna.growth_vector)


# ── Sprint 36 WS-6: Target Role Update ────────────────────────


@router.put(
    "/growth/target-role",
    response_model=GrowthVectorResponse,
    summary="Update target career role",
)
@limiter.limit("10/minute")
async def update_target_role(
    request: Request,
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GrowthVectorResponse:
    """
    Set or update the user's target career role.

    Triggers async recalculation of growth trajectory.
    Logs the change to UserActivityLog (not AdminAuditLog — Audit F24).
    """
    import re

    from app.models.user_activity import UserActivityLog

    # Validate + sanitize input
    raw_target_role = payload.get("target_role", "")
    if not isinstance(raw_target_role, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_role must be a string.",
        )

    # Sprint 36 Audit F29: sanitize user text — strip HTML tags
    sanitized_role = re.sub(r"<[^>]+>", "", raw_target_role).strip()

    if not sanitized_role or len(sanitized_role) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_role must be 1-255 characters after sanitization.",
        )

    # Load growth vector
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id,
    )
    if career_dna is None or career_dna.growth_vector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Growth vector not found. Generate Career DNA first.",
        )

    previous_role = career_dna.growth_vector.target_role
    career_dna.growth_vector.target_role = sanitized_role

    # Log activity (Audit F24: UserActivityLog, not AdminAuditLog)
    activity = UserActivityLog(
        user_id=current_user.id,
        action="target_role_update",
        entity_type="growth_vector",
        entity_id=career_dna.growth_vector.id,
        details={
            "previous": previous_role,
            "new": sanitized_role,
        },
    )
    db.add(activity)

    await db.commit()

    return GrowthVectorResponse.model_validate(career_dna.growth_vector)


@router.get(
    "/values",
    response_model=ValuesProfileResponse,
    summary="Get values alignment profile",
)
async def get_values_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ValuesProfileResponse:
    """Get career values alignment assessment."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None or career_dna.values_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Values profile not found.",
        )
    return ValuesProfileResponse.model_validate(career_dna.values_profile)


@router.get(
    "/market",
    response_model=MarketPositionResponse,
    summary="Get market position snapshot",
)
async def get_market_position(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketPositionResponse:
    """Get real-time market standing snapshot."""
    career_dna = await CareerDNAService.get_full_profile(
        db, user_id=current_user.id
    )
    if career_dna is None or career_dna.market_position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market position not found.",
        )
    return MarketPositionResponse.model_validate(career_dna.market_position)


# ── Hidden Skills Management ──────────────────────────────────


@router.patch(
    "/hidden-skills/{skill_id}",
    response_model=HiddenSkillResponse,
    summary="Confirm or reject a hidden skill",
)
async def confirm_hidden_skill(
    skill_id: uuid.UUID,
    payload: HiddenSkillConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HiddenSkillResponse:
    """Human-in-the-loop: let the user confirm or reject a discovered skill."""
    skill = await CareerDNAService.confirm_hidden_skill(
        db,
        user_id=current_user.id,
        skill_id=skill_id,
        confirmed=payload.confirmed,
    )
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hidden skill not found.",
        )
    await db.commit()
    return _hidden_skill_response(skill)


# ── Response Builders ──────────────────────────────────────────


def _build_full_response(career_dna: CareerDNA) -> CareerDNAResponse:
    """Build full Career DNA response from ORM model."""
    from app.schemas.career_dna import SkillGenomeResponse

    genome = SkillGenomeResponse(
        explicit_skills=[
            _skill_entry_response(entry) for entry in career_dna.skill_genome
        ],
        hidden_skills=[
            _hidden_skill_response(skill) for skill in career_dna.hidden_skills
        ],
        total_skills=len(career_dna.skill_genome) + len(career_dna.hidden_skills),
    ) if career_dna.skill_genome else None

    return CareerDNAResponse(
        id=career_dna.id,
        completeness_score=career_dna.completeness_score,
        last_analysis_at=career_dna.last_analysis_at,
        version=career_dna.version,
        summary=career_dna.summary,
        skill_genome=genome,
        experience_blueprint=(
            ExperienceBlueprintResponse.model_validate(
                career_dna.experience_blueprint
            )
            if career_dna.experience_blueprint
            else None
        ),
        growth_vector=(
            GrowthVectorResponse.model_validate(career_dna.growth_vector)
            if career_dna.growth_vector
            else None
        ),
        values_profile=(
            ValuesProfileResponse.model_validate(career_dna.values_profile)
            if career_dna.values_profile
            else None
        ),
        market_position=(
            MarketPositionResponse.model_validate(career_dna.market_position)
            if career_dna.market_position
            else None
        ),
        hidden_skills=[
            _hidden_skill_response(skill)
            for skill in career_dna.hidden_skills
        ],
    )


def _skill_entry_response(entry: SkillGenomeEntry) -> SkillGenomeEntryResponse:
    """Convert ORM skill genome entry to response schema."""
    from app.schemas.career_dna import SkillGenomeEntryResponse

    return SkillGenomeEntryResponse(
        id=entry.id,
        skill_name=entry.skill_name,
        category=entry.category,
        proficiency_level=entry.proficiency_level,
        source=entry.source,
        confidence=entry.confidence,
        evidence=entry.evidence,
        years_experience=entry.years_experience,
        last_used_date=entry.last_used_date,
    )


def _hidden_skill_response(skill: HiddenSkill) -> HiddenSkillResponse:
    """Convert ORM hidden skill to response schema."""
    return HiddenSkillResponse(
        id=skill.id,
        skill_name=skill.skill_name,
        discovery_method=skill.discovery_method,
        confidence=skill.confidence,
        evidence=skill.evidence,
        user_confirmed=skill.user_confirmed,
        source_text=skill.source_text,
    )
