"""
PathForge API — Resume Upload Routes
======================================
File upload endpoint: parse PDF, DOCX, TXT, or image → structured resume.

Sprint 50: Initial implementation of multipart file upload with integrated
document parsing (including OCR for images) and LLM-powered structure extraction.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.services.document_parser import (
    SUPPORTED_EXTENSIONS,
    DocumentParseError,
    FileTooLargeError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


# ── Response Schemas ──────────────────────────────────────────


class ResumeUploadResponse(BaseModel):
    """Response from a successful resume file upload."""

    resume_id: str
    version: int
    raw_text_length: int
    structured_data: dict[str, Any] | None = None
    ocr_used: bool = False
    message: str


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
    from pathlib import PurePath

    from app.ai.resume_parser import ResumeParser
    from app.services.resume_service import ResumeService

    # ── Validate filename ──────────────────────────────────────
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

    # ── Read file bytes ────────────────────────────────────────
    file_bytes = await file.read()

    # ── Parse document → raw text ──────────────────────────────
    is_image = extension in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    try:
        from app.services.document_parser import parse_document
        raw_text = await parse_document(file_bytes=file_bytes, filename=file.filename)
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
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

    # ── LLM structure extraction (optional) ───────────────────
    structured: dict[str, Any] | None = None
    if parse_structured:
        try:
            parser = ResumeParser()
            parsed = await parser.parse(raw_text)
            structured = parsed if isinstance(parsed, dict) else parsed.model_dump()
        except Exception:
            logger.warning(
                "LLM resume parsing failed for user %s — saving raw text only",
                current_user.id,
            )

    # ── Save to database ───────────────────────────────────────
    title = file.filename or "Uploaded Resume"
    resume = await ResumeService.create(
        db,
        user_id=current_user.id,
        title=title[:255],
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
    summary="List all resumes for the current user",
)
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all resumes for the authenticated user, newest first."""
    from app.services.resume_service import ResumeService

    resumes = await ResumeService.get_by_user(db, current_user.id)
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "version": r.version,
            "raw_text_length": len(r.raw_text or ""),
            "has_structured_data": r.structured_data is not None,
            "has_embedding": r.embedding is not None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in resumes
    ]
