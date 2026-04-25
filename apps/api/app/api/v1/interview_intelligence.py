"""
PathForge API v1 — Interview Intelligence™ Endpoints
=======================================================
REST endpoints for the Interview Intelligence Engine.

11 endpoints at /api/v1/interview-intelligence:
    GET    /dashboard                         — All saved preps + preferences
    POST   /prep                              — Create interview prep session
    POST   /compare                           — Compare interview preps
    GET    /preferences                       — Get interview preferences
    PUT    /preferences                       — Update interview preferences
    GET    /{prep_id}                         — Get specific interview prep
    DELETE /{prep_id}                         — Delete an interview prep
    POST   /{prep_id}/questions               — Generate additional questions
    POST   /{prep_id}/star-examples           — Generate STAR examples
    POST   /{prep_id}/negotiation-script      — Generate negotiation script
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.interview_intelligence import (
    GenerateNegotiationScriptRequest,
    GenerateQuestionsRequest,
    GenerateSTARExamplesRequest,
    InterviewDashboardResponse,
    InterviewPreferenceResponse,
    InterviewPreferenceUpdateRequest,
    InterviewPrepCompareRequest,
    InterviewPrepComparisonResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    InterviewPrepSummaryResponse,
    NegotiationScriptResponse,
)
from app.services import interview_intelligence_service
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/interview-intelligence",
    tags=["Interview Intelligence"],
)


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=InterviewDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Interview intelligence dashboard",
    description="Retrieve all saved interview preps, preferences, and summary statistics.",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewDashboardResponse:
    """Retrieve all saved interview preps and preferences for dashboard."""
    data = await interview_intelligence_service.get_dashboard(
        database, user_id=current_user.id,
    )

    return InterviewDashboardResponse(
        preps=[
            InterviewPrepSummaryResponse.model_validate(prep)
            for prep in data["preps"]
        ],
        preferences=(
            InterviewPreferenceResponse.model_validate(data["preferences"])
            if data["preferences"]
            else None
        ),
        total_preps=data["total_preps"],
        company_counts=data["company_counts"],
    )


# ── Create Interview Prep ─────────────────────────────────────


@router.post(
    "/prep",
    response_model=InterviewPrepResponse,
    status_code=HTTP_201_CREATED,
    summary="Create interview preparation",
    description=(
        "Create a company-specific interview preparation session. "
        "Analyzes the company, generates questions, and maps STAR examples from Career DNA."
    ),
    dependencies=[Depends(require_feature("interview_intelligence"))],
)
@limiter.limit("5/minute")
async def create_prep(
    request: Request,
    body: InterviewPrepRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Create a new interview prep session."""
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "interview_intelligence")

    prep = await interview_intelligence_service.create_interview_prep(
        database,
        user_id=current_user.id,
        company_name=body.company_name,
        target_role=body.target_role,
        prep_depth=body.prep_depth,
    )
    # C2: Record usage after successful scan
    if settings.billing_enabled:
        await BillingService.record_usage(database, current_user, "interview_intelligence")

    return InterviewPrepResponse.model_validate(prep)


# ── Compare Preps ─────────────────────────────────────────────


@router.post(
    "/compare",
    response_model=InterviewPrepComparisonResponse,
    status_code=HTTP_200_OK,
    summary="Compare interview preps",
    description="Compare 2-5 saved interview preps side-by-side.",
)
@limiter.limit("3/minute")
async def compare_preps(
    request: Request,
    body: InterviewPrepCompareRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPrepComparisonResponse:
    """Compare multiple interview preps."""
    data = await interview_intelligence_service.compare_interview_preps(
        database,
        user_id=current_user.id,
        prep_ids=body.prep_ids,
    )

    return InterviewPrepComparisonResponse(
        preps=[
            InterviewPrepResponse.model_validate(prep)
            for prep in data["preps"]
        ],
        ranking=data.get("ranking", []),
        comparison_summary=data.get("comparison_summary"),
    )


# ── Preferences ────────────────────────────────────────────────
# NOTE: Must be defined BEFORE /{prep_id} to avoid path collision.


@router.get(
    "/preferences",
    response_model=InterviewPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get interview preferences",
    description="Retrieve your Interview Intelligence preferences.",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPreferenceResponse | None:
    """Retrieve interview preferences for the current user."""
    preference = await interview_intelligence_service.get_preferences(
        database, user_id=current_user.id,
    )
    if not preference:
        return None

    return InterviewPreferenceResponse.model_validate(preference)


@router.put(
    "/preferences",
    response_model=InterviewPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update interview preferences",
    description="Update or create your Interview Intelligence preferences.",
)
async def update_preferences(
    body: InterviewPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPreferenceResponse:
    """Update or create interview preferences."""
    preference = await interview_intelligence_service.update_preferences(
        database,
        user_id=current_user.id,
        update_data=body,
    )
    return InterviewPreferenceResponse.model_validate(preference)


# ── Get / Delete Interview Prep ────────────────────────────────


@router.get(
    "/{prep_id}",
    response_model=InterviewPrepResponse,
    status_code=HTTP_200_OK,
    summary="Get interview prep detail",
    description="Retrieve a specific interview prep with all insights, questions, and STAR examples.",
    responses={HTTP_404_NOT_FOUND: {"description": "Interview prep not found"}},
)
async def get_prep(
    prep_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Retrieve a specific interview prep by ID."""
    prep = await interview_intelligence_service.get_interview_prep(
        database, prep_id=prep_id, user_id=current_user.id,
    )
    if not prep:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    return InterviewPrepResponse.model_validate(prep)


@router.delete(
    "/{prep_id}",
    status_code=HTTP_204_NO_CONTENT,
    summary="Delete interview prep",
    description="Delete a saved interview prep and all related data.",
    responses={HTTP_404_NOT_FOUND: {"description": "Interview prep not found"}},
)
async def delete_prep(
    prep_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> None:
    """Delete an interview prep."""
    deleted = await interview_intelligence_service.delete_interview_prep(
        database, prep_id=prep_id, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )


# ── Generate: Questions ────────────────────────────────────────


@router.post(
    "/{prep_id}/questions",
    response_model=InterviewPrepResponse,
    status_code=HTTP_201_CREATED,
    summary="Generate interview questions",
    description="Generate additional company-specific interview questions for an existing prep.",
    responses={HTTP_404_NOT_FOUND: {"description": "Interview prep not found"}},
)
@limiter.limit("5/minute")
async def generate_questions(
    request: Request,
    prep_id: uuid.UUID,
    body: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate additional questions for an interview prep."""
    prep = await interview_intelligence_service.generate_questions_for_prep(
        database,
        prep_id=prep_id,
        user_id=current_user.id,
        category_filter=body.category_filter,
        max_questions=body.max_questions,
    )
    if not prep:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    return InterviewPrepResponse.model_validate(prep)


# ── Generate: STAR Examples ───────────────────────────────────


@router.post(
    "/{prep_id}/star-examples",
    response_model=InterviewPrepResponse,
    status_code=HTTP_201_CREATED,
    summary="Generate STAR examples",
    description="Generate Career DNA-mapped STAR examples for an existing prep.",
    responses={HTTP_404_NOT_FOUND: {"description": "Interview prep not found"}},
)
@limiter.limit("5/minute")
async def generate_star_examples(
    request: Request,
    prep_id: uuid.UUID,
    body: GenerateSTARExamplesRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate STAR examples mapped from Career DNA."""
    prep = await interview_intelligence_service.generate_star_examples_for_prep(
        database,
        prep_id=prep_id,
        user_id=current_user.id,
        max_examples=body.max_examples,
    )
    if not prep:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    return InterviewPrepResponse.model_validate(prep)


# ── Generate: Negotiation Script ──────────────────────────────


@router.post(
    "/{prep_id}/negotiation-script",
    response_model=NegotiationScriptResponse,
    status_code=HTTP_201_CREATED,
    summary="Generate negotiation script",
    description=(
        "Generate data-backed salary negotiation scripts using "
        "Salary Intelligence Engine™ data."
    ),
    responses={HTTP_404_NOT_FOUND: {"description": "Interview prep not found"}},
)
@limiter.limit("3/minute")
async def generate_negotiation_script(
    request: Request,
    prep_id: uuid.UUID,
    body: GenerateNegotiationScriptRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NegotiationScriptResponse:
    """Generate salary negotiation scripts for an interview prep."""
    script_data = await interview_intelligence_service.generate_negotiation_script(
        database,
        prep_id=prep_id,
        user_id=current_user.id,
        target_salary=body.target_salary,
        currency=body.currency,
    )
    return NegotiationScriptResponse(**script_data)
