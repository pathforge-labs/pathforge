"""
PathForge API — Resume Upload Routes
======================================
File upload endpoint: parse PDF, DOCX, TXT, or image → structured resume.

Sprint 50: Initial implementation of multipart file upload with integrated
document parsing (including OCR for images) and LLM-powered structure extraction.
"""

from __future__ import annotations

import logging
from pathlib import PurePath
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.resume_parser import ResumeParser
from app.core.database import get_db
from app.core.prompt_sanitizer import sanitize_user_text
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.services.document_parser import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    DocumentParseError,
    FileTooLargeError,
    UnsupportedFormatError,
    parse_document,
)
from app.services.resume_service import ResumeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])

RESUME_TITLE_MAX_LENGTH = 255


# ── Response Schemas ──────────────────────────────────────────


class ResumeUploadResponse(BaseModel):
    """Response from a successful resume file upload."""

    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    version: int
    raw_text_length: int
    structured_data: dict[str, Any] | None = None
    ocr_used: bool = False
    message: str


class ResumeSummaryResponse(BaseModel):
    """Summary entry for a resume in the listing response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    version: int
    raw_text_length: int
    has_structured_data: bool
    has_embedding: bool
    created_at: str | None


# ── Helpers ───────────────────────────────────────────────────


async def _parse_and_sanitize(file_bytes: bytes, filename: str) -> str:
    """Extract text from file bytes and sanitize for LLM input."""
    raw_text = await parse_document(file_bytes=file_bytes, filename=filename)
    clean_text, _ = sanitize_user_text(raw_text)
    return clean_text


async def _extract_structured(raw_text: str, user_id: Any) -> dict[str, Any] | None:
    """Run LLM structure extraction; return None on failure (graceful degradation)."""
    try:
        parser = ResumeParser()
        parsed = await parser.parse(raw_text)
        return parsed if isinstance(parsed, dict) else parsed.model_dump()
    except Exception:
        logger.exception(
            "LLM resume parsing failed for user %s — saving raw text only", user_id,
        )
        return None


# ── Endpoint ──────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a resume file",
    description=(
        "Upload a resume as PDF, DOCX, TXT, or image (JPEG/PNG/WebP/GIF). "
        "The file is parsed to extract raw text, then optionally structured "
        "via the AI parsing pipeline. The resume is saved and linked to your "
        "account."
    ),
)
@limiter.limit("10/minute")
async def upload_resume(
    request: Request,
    file: UploadFile,
    parse_structured: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    """Upload a resume file, extract text, optionally parse structure, and save."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    extension = PurePath(file.filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file format '{extension}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    file_bytes = await file.read()
    is_image = extension in SUPPORTED_IMAGE_EXTENSIONS

    try:
        raw_text = await _parse_and_sanitize(file_bytes, file.filename)
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except DocumentParseError as exc:
        logger.error("Document parsing failed for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse document: {exc}",
        ) from exc

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the uploaded file.",
        )

    structured = await _extract_structured(raw_text, current_user.id) if parse_structured else None

    resume = await ResumeService.create(
        db,
        user_id=current_user.id,
        title=(file.filename or "Uploaded Resume")[:RESUME_TITLE_MAX_LENGTH],
        raw_text=raw_text,
    )

    if structured is not None:
        resume.structured_data = structured
        await db.flush()

    await db.commit()
    await db.refresh(resume)

    logger.info(
        "Resume uploaded: user=%s resume_id=%s version=%d ocr=%s",
        current_user.id, resume.id, resume.version, is_image,
    )

    return ResumeUploadResponse(
        resume_id=str(resume.id),
        version=resume.version,
        raw_text_length=len(raw_text),
        structured_data=structured,
        ocr_used=is_image,
        message=(
            "Resume uploaded and parsed successfully."
            if structured
            else "Resume uploaded. Text extracted; structured parsing unavailable."
        ),
    )


@router.get(
    "/",
    response_model=list[ResumeSummaryResponse],
    summary="List all resumes for the current user",
)
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeSummaryResponse]:
    """Return all resumes for the authenticated user, newest first."""
    resumes = await ResumeService.get_by_user(db, current_user.id)
    return [
        ResumeSummaryResponse(
            id=str(r.id),
            title=r.title,
            version=r.version,
            raw_text_length=len(r.raw_text or ""),
            has_structured_data=r.structured_data is not None,
            has_embedding=r.embedding is not None,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in resumes
    ]
