"""
PathForge API — AI Engine Routes
===================================
AI-powered resume parsing, embedding, matching, and CV tailoring.

All endpoints are JWT-protected.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.matching import JobListing
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Engine"])


# ── Request / Response Schemas ─────────────────────────────────


class ParseResumeRequest(BaseModel):
    """Request body for resume parsing."""

    raw_text: str = Field(
        ...,
        min_length=50,
        max_length=100_000,
        description="Raw resume/CV text to parse (max 100KB)",
    )


class ParseResumeResponse(BaseModel):
    """Response from resume parsing."""

    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)


class EmbedResumeResponse(BaseModel):
    """Response from resume embedding."""

    resume_id: str
    dimensions: int
    message: str = "Embedding generated and stored successfully"


class MatchRequest(BaseModel):
    """Request body for matching."""

    top_k: int = Field(default=20, ge=1, le=100, description="Number of matches to return")


class MatchCandidateResponse(BaseModel):
    """A single match result."""

    job_id: str
    score: float
    title: str = ""
    company: str = ""


class MatchResponse(BaseModel):
    """Response from semantic matching."""

    resume_id: str
    matches: list[MatchCandidateResponse]
    total: int


class TailorCVRequest(BaseModel):
    """Request body for CV tailoring."""

    resume_id: uuid.UUID = Field(..., description="UUID of the resume to tailor")
    job_id: uuid.UUID = Field(..., description="UUID of the target job listing")


class TailorCVResponse(BaseModel):
    """Response from CV tailoring."""

    tailored_summary: str = ""
    tailored_skills: list[str] = Field(default_factory=list)
    tailored_experience: list[str] = Field(default_factory=list)
    diffs: list[dict[str, Any]] = Field(default_factory=list)
    ats_score: int = 0
    ats_suggestions: list[str] = Field(default_factory=list)


# ── Endpoints ──────────────────────────────────────────────────


@router.post(
    "/parse-resume",
    response_model=ParseResumeResponse,
    summary="Parse raw resume text into structured data",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_parse)
@route_query_budget(max_queries=3)
async def parse_resume(
    request: Request,
    payload: ParseResumeRequest,
    _current_user: User = Depends(get_current_user),
) -> ParseResumeResponse:
    """
    Send raw resume/CV text and receive structured extracted data.

    Uses LLM-powered extraction (Fast tier) for ~95% accuracy.
    """
    from app.ai.resume_parser import ResumeParser

    parsed = await ResumeParser.parse(payload.raw_text)
    return ParseResumeResponse(
        full_name=parsed.full_name,
        email=parsed.email,
        phone=parsed.phone,
        location=parsed.location,
        summary=parsed.summary,
        skills=[s.model_dump() for s in parsed.skills],
        experience=[e.model_dump() for e in parsed.experience],
        education=[e.model_dump() for e in parsed.education],
        certifications=[c.model_dump() for c in parsed.certifications],
        languages=[lang.model_dump() for lang in parsed.languages],
    )


@router.post(
    "/embed-resume/{resume_id}",
    response_model=EmbedResumeResponse,
    summary="Generate and store embedding for a resume",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_embed)
@route_query_budget(max_queries=4)
async def embed_resume(
    request: Request,
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmbedResumeResponse:
    """
    Generate a Voyage AI embedding for the specified resume and store it in the database.

    The resume must belong to the authenticated user.
    """
    from app.ai.embeddings import EmbeddingService
    from app.ai.resume_parser import ResumeParser
    from app.services.resume_service import ResumeService

    resume = await ResumeService.get_by_id(db, resume_id, current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resume",
        )

    # Parse raw text if available, then embed
    if resume.raw_text:
        parsed = await ResumeParser.parse(resume.raw_text)
        embedding_service = EmbeddingService()
        embedding = await embedding_service.embed_resume(parsed)

        # Store embedding on the resume record
        resume.embedding = embedding
        await db.commit()

        return EmbedResumeResponse(
            resume_id=str(resume_id),
            dimensions=len(embedding),
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Resume has no raw text to embed",
    )


@router.post(
    "/match/{resume_id}",
    response_model=MatchResponse,
    summary="Find semantically matching jobs for a resume",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_match)
@route_query_budget(max_queries=4)
async def match_resume(
    request: Request,
    resume_id: uuid.UUID,
    payload: MatchRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """
    Run semantic matching against job listings using the resume's embedding.

    The resume must have a stored embedding (call embed-resume first).
    """
    from app.ai.matching import MatchingService
    from app.services.resume_service import ResumeService

    resume = await ResumeService.get_by_id(db, resume_id, current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resume",
        )
    if not resume.embedding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has no embedding. Call POST /ai/embed-resume/{id} first.",
        )

    top_k = payload.top_k if payload else 20
    candidates = await MatchingService.find_matches(
        db, resume_embedding=list(resume.embedding), top_k=top_k
    )

    return MatchResponse(
        resume_id=str(resume_id),
        matches=[
            MatchCandidateResponse(
                job_id=c.job_id,
                score=c.score,
                title=c.title,
                company=c.company,
            )
            for c in candidates
        ],
        total=len(candidates),
    )


@router.post(
    "/tailor-cv",
    response_model=TailorCVResponse,
    summary="Generate a tailored CV for a specific job",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_tailor)
@route_query_budget(max_queries=4)
async def tailor_cv(
    request: Request,
    payload: TailorCVRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TailorCVResponse:
    """
    Generate a tailored CV version for a job listing.

    The original resume content is reorganized and rephrased —
    never fabricated — to maximize ATS compatibility and relevance.
    Returns field-level diffs showing exactly what changed and why.
    """
    from app.ai.cv_tailor import CVTailoringService
    from app.ai.resume_parser import ResumeParser
    from app.services.resume_service import ResumeService

    resume_id = payload.resume_id
    job_id = payload.job_id

    resume = await ResumeService.get_by_id(db, resume_id, current_user.id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resume",
        )

    # Get job listing

    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job listing not found",
        )

    # Parse resume, then tailor
    parsed = await ResumeParser.parse(resume.raw_text or "")

    tailored = await CVTailoringService.generate_tailored_cv(
        resume=parsed,
        job_title=job.title,
        job_company=job.company,
        job_description=job.description or "",
    )

    return TailorCVResponse(
        tailored_summary=tailored.tailored_summary,
        tailored_skills=tailored.tailored_skills,
        tailored_experience=tailored.tailored_experience,
        diffs=[d.model_dump() for d in tailored.diffs],
        ats_score=tailored.ats_score,
        ats_suggestions=tailored.ats_suggestions,
    )


# ── Job Ingestion ──────────────────────────────────────────────


class IngestJobsRequest(BaseModel):
    """Request body for job ingestion."""

    keywords: str = Field(..., min_length=2, max_length=200, description="Search keywords")
    location: str = Field("", max_length=200, description="Location filter")
    country: str = Field("nl", max_length=5, description="ISO 3166-1 alpha-2 country code")
    pages: int = Field(1, ge=1, le=10, description="Number of pages per provider")
    results_per_page: int = Field(20, ge=1, le=50, description="Results per page")
    embed: bool = Field(True, description="Embed new listings after ingestion")


class IngestJobsResponse(BaseModel):
    """Response for job ingestion."""

    total_fetched: int
    total_new: int
    total_duplicates: int
    providers: list[dict[str, Any]]
    embedded: int = 0


@router.post(
    "/ingest-jobs",
    response_model=IngestJobsResponse,
    summary="Ingest job listings from external APIs",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_parse)
@route_query_budget(max_queries=3)
async def ingest_jobs(
    request: Request,
    payload: IngestJobsRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> IngestJobsResponse:
    """
    Trigger job ingestion from configured providers (Adzuna, Jooble).

    Fetches jobs, deduplicates against DB, inserts new listings,
    and optionally embeds them for semantic matching.
    """
    from app.jobs.ingestion import ingest_jobs as run_ingestion
    from app.jobs.providers.adzuna import AdzunaProvider
    from app.jobs.providers.base import JobProvider
    from app.jobs.providers.jooble import JoobleProvider

    # Build list of configured providers
    providers: list[JobProvider] = []
    if settings.adzuna_app_id and settings.adzuna_app_key:
        providers.append(AdzunaProvider())
    if settings.jooble_api_key:
        providers.append(JoobleProvider())

    if not providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No job providers configured. Set ADZUNA_APP_ID/ADZUNA_APP_KEY or JOOBLE_API_KEY.",
        )

    result = await run_ingestion(
        session=db,
        providers=providers,
        keywords=payload.keywords,
        location=payload.location,
        country=payload.country,
        pages=payload.pages,
        results_per_page=payload.results_per_page,
    )

    embedded = 0
    if payload.embed and result.total_new > 0:
        try:
            from app.jobs.embed_pipeline import embed_new_jobs

            embedded = await embed_new_jobs(session=db)
        except (ValueError, RuntimeError, ImportError):
            import logging

            logging.getLogger(__name__).exception("Embedding failed, jobs saved without embeddings")

    return IngestJobsResponse(
        total_fetched=result.total_fetched,
        total_new=result.total_new,
        total_duplicates=result.total_duplicates,
        providers=[s.to_dict() for s in result.providers],
        embedded=embedded,
    )
