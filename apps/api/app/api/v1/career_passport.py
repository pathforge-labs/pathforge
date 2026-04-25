"""
PathForge API v1 — Cross-Border Career Passport™ Endpoints
=============================================================
REST endpoints for the Cross-Border Career Passport.

11 endpoints at /api/v1/career-passport:
    GET  /dashboard                    — Aggregated passport dashboard
    POST /scan                         — Full passport analysis
    POST /credential-mapping           — Map single qualification
    GET  /credential-mapping/{id}      — Retrieve mapping
    DELETE /credential-mapping/{id}    — Delete mapping
    POST /country-comparison           — Compare two countries
    POST /multi-country-comparison     — Compare up to 5 countries
    POST /visa-assessment              — Visa feasibility
    GET  /market-demand/{country}      — Market demand snapshot
    GET  /preferences                  — Get preferences
    PUT  /preferences                  — Update preferences
"""

from __future__ import annotations

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
from app.schemas.career_passport import (
    CareerPassportDashboardResponse,
    CareerPassportPreferenceResponse,
    CareerPassportPreferenceUpdate,
    CountryComparisonRequest,
    CountryComparisonResponse,
    CredentialMappingRequest,
    CredentialMappingResponse,
    MarketDemandResponse,
    MultiCountryComparisonRequest,
    MultiCountryComparisonResponse,
    PassportScanResponse,
    PassportScoreResponse,
    VisaAssessmentRequest,
    VisaAssessmentResponse,
)
from app.services import career_passport_service
from app.services.billing_service import BillingService

router = APIRouter(
    prefix="/career-passport",
    tags=["Career Passport"],
)


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=CareerPassportDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Get career passport dashboard",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerPassportDashboardResponse:
    """Retrieve aggregated passport data: mappings, comparisons, scores."""
    dashboard = await career_passport_service.get_dashboard(
        database, user_id=current_user.id,
    )

    mapping_responses = [
        CredentialMappingResponse.model_validate(mapping)
        for mapping in dashboard["credential_mappings"]
    ]
    comparison_responses = [
        CountryComparisonResponse.model_validate(comp)
        for comp in dashboard["country_comparisons"]
    ]
    visa_responses = [
        VisaAssessmentResponse.model_validate(visa)
        for visa in dashboard["visa_assessments"]
    ]
    demand_responses = [
        MarketDemandResponse.model_validate(demand)
        for demand in dashboard["market_demand"]
    ]

    pref_response = None
    if dashboard["preferences"]:
        pref_response = CareerPassportPreferenceResponse.model_validate(
            dashboard["preferences"],
        )

    score_responses = [
        PassportScoreResponse(**score)
        for score in dashboard["passport_scores"]
    ]

    return CareerPassportDashboardResponse(
        credential_mappings=mapping_responses,
        country_comparisons=comparison_responses,
        visa_assessments=visa_responses,
        market_demand=demand_responses,
        preferences=pref_response,
        passport_scores=score_responses,
    )


# ── Full Passport Scan ────────────────────────────────────────


@router.post(
    "/scan",
    response_model=PassportScanResponse,
    status_code=HTTP_201_CREATED,
    summary="Full passport scan",
    dependencies=[Depends(require_feature("career_passport"))],
)
@limiter.limit("3/minute")
async def full_scan(
    request: Request,
    body: CredentialMappingRequest,
    nationality: str = "Not specified",
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PassportScanResponse:
    """Execute full passport analysis for a target country.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "career_passport")

    try:
        result = await career_passport_service.full_passport_scan(
            database,
            user_id=current_user.id,
            source_qualification=body.source_qualification,
            source_country=body.source_country,
            target_country=body.target_country,
            nationality=nationality,
        )

        # C2: Record usage after successful scan
        if settings.billing_enabled:
            await BillingService.record_usage(database, current_user, "career_passport")

        return PassportScanResponse(
            credential_mapping=CredentialMappingResponse.model_validate(
                result["credential_mapping"],
            ),
            country_comparison=CountryComparisonResponse.model_validate(
                result["country_comparison"],
            ),
            visa_assessment=VisaAssessmentResponse.model_validate(
                result["visa_assessment"],
            ),
            market_demand=MarketDemandResponse.model_validate(
                result["market_demand"],
            ),
            passport_score=PassportScoreResponse(**result["passport_score"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Credential Mapping ────────────────────────────────────────


@router.post(
    "/credential-mapping",
    response_model=CredentialMappingResponse,
    status_code=HTTP_201_CREATED,
    summary="Map a qualification",
)
@limiter.limit("5/minute")
async def create_credential_mapping(
    request: Request,
    body: CredentialMappingRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CredentialMappingResponse:
    """Map a qualification to its international EQF equivalent."""
    try:
        mapping = await career_passport_service.map_credential(
            database,
            user_id=current_user.id,
            source_qualification=body.source_qualification,
            source_country=body.source_country,
            target_country=body.target_country,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CredentialMappingResponse.model_validate(mapping)


@router.get(
    "/credential-mapping/{mapping_id}",
    response_model=CredentialMappingResponse,
    status_code=HTTP_200_OK,
    summary="Get credential mapping",
)
async def get_credential_mapping(
    mapping_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CredentialMappingResponse:
    """Retrieve a specific credential mapping by ID."""
    mapping = await career_passport_service.get_credential_mapping(
        database, mapping_id=mapping_id, user_id=current_user.id,
    )
    if not mapping:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Credential mapping not found.",
        )
    return CredentialMappingResponse.model_validate(mapping)


@router.delete(
    "/credential-mapping/{mapping_id}",
    status_code=HTTP_204_NO_CONTENT,
    summary="Delete credential mapping",
)
async def delete_credential_mapping(
    mapping_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> None:
    """Delete a credential mapping by ID."""
    deleted = await career_passport_service.delete_credential_mapping(
        database, mapping_id=mapping_id, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Credential mapping not found.",
        )


# ── Country Comparison ─────────────────────────────────────────


@router.post(
    "/country-comparison",
    response_model=CountryComparisonResponse,
    status_code=HTTP_201_CREATED,
    summary="Compare two countries",
)
@limiter.limit("5/minute")
async def create_country_comparison(
    request: Request,
    body: CountryComparisonRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CountryComparisonResponse:
    """Compare two countries for career mobility."""
    try:
        comparison = await career_passport_service.compare_countries(
            database,
            user_id=current_user.id,
            source_country=body.source_country,
            target_country=body.target_country,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CountryComparisonResponse.model_validate(comparison)


@router.post(
    "/multi-country-comparison",
    response_model=MultiCountryComparisonResponse,
    status_code=HTTP_201_CREATED,
    summary="Compare up to 5 countries",
)
@limiter.limit("2/minute")
async def multi_country_comparison(
    request: Request,
    body: MultiCountryComparisonRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> MultiCountryComparisonResponse:
    """Compare up to 5 target countries side-by-side."""
    try:
        result = await career_passport_service.compare_multiple_countries(
            database,
            user_id=current_user.id,
            source_country=body.source_country,
            target_countries=body.target_countries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return MultiCountryComparisonResponse(
        comparisons=[
            CountryComparisonResponse.model_validate(comp)
            for comp in result["comparisons"]
        ],
        passport_scores=[
            PassportScoreResponse(**score)
            for score in result["passport_scores"]
        ],
        recommended_country=result.get("recommended_country"),
        recommendation_reasoning=result.get("recommendation_reasoning"),
    )


# ── Visa Assessment ────────────────────────────────────────────


@router.post(
    "/visa-assessment",
    response_model=VisaAssessmentResponse,
    status_code=HTTP_201_CREATED,
    summary="Assess visa feasibility",
)
@limiter.limit("5/minute")
async def create_visa_assessment(
    request: Request,
    body: VisaAssessmentRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> VisaAssessmentResponse:
    """Assess visa/work permit feasibility for a target country."""
    try:
        assessment = await career_passport_service.assess_visa(
            database,
            user_id=current_user.id,
            nationality=body.nationality,
            target_country=body.target_country,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return VisaAssessmentResponse.model_validate(assessment)


# ── Market Demand ──────────────────────────────────────────────


@router.get(
    "/market-demand/{country}",
    response_model=list[MarketDemandResponse],
    status_code=HTTP_200_OK,
    summary="Get market demand for country",
)
async def get_market_demand(
    country: str,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[MarketDemandResponse]:
    """Get all market demand entries for a specific country."""
    entries = await career_passport_service.get_market_demand_by_country(
        database, country=country, user_id=current_user.id,
    )
    return [
        MarketDemandResponse.model_validate(entry)
        for entry in entries
    ]


# ── Preferences ────────────────────────────────────────────────
# NOTE: Must be defined BEFORE any /{param_id} to avoid path collision.


@router.get(
    "/preferences",
    response_model=CareerPassportPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get career passport preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerPassportPreferenceResponse | None:
    """Retrieve Career Passport preferences."""
    pref = await career_passport_service.get_preferences(
        database, user_id=current_user.id,
    )
    if not pref:
        return None
    return CareerPassportPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=CareerPassportPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update career passport preferences",
)
async def update_preferences(
    body: CareerPassportPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerPassportPreferenceResponse:
    """Update or create Career Passport preferences."""
    try:
        pref = await career_passport_service.update_preferences(
            database, user_id=current_user.id, update_data=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CareerPassportPreferenceResponse.model_validate(pref)
