"""
PathForge — Document Parser
==============================
Secure document parsing for resume uploads (PDF, DOCX, TXT, and images).

Security features (Sprint 29):
- File size limit: 10 MB
- Page limit: 100 pages (memory guard — audit H3)
- MIME verification via filetype library (audit H5)
- Encrypted PDF rejection
- Macro-enabled DOCX rejection
- Sandboxed parsing via asyncio.to_thread()

Sprint 50: Added image support (JPEG, PNG, WebP, GIF) via OCR service.

Usage:
    from app.services.document_parser import parse_document

    text = await parse_document(file_bytes=content, filename="resume.pdf")
    text = await parse_document(file_bytes=content, filename="resume.jpg")
"""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import PurePath

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
MAX_PAGES: int = 100  # Memory guard (audit H3)

# Document formats
_DOC_EXTENSIONS: frozenset[str] = frozenset({".txt", ".pdf", ".docx"})

# Image formats (routed through OCR service)
_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

SUPPORTED_EXTENSIONS: frozenset[str] = _DOC_EXTENSIONS | _IMAGE_EXTENSIONS

# MIME types validated against actual file content (documents only)
EXPECTED_MIMES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ── Custom Exceptions ─────────────────────────────────────────


class DocumentParseError(Exception):
    """Base exception for document parsing failures."""


class FileTooLargeError(DocumentParseError):
    """File exceeds the maximum allowed size."""


class UnsupportedFormatError(DocumentParseError):
    """File format is not supported."""


class MimeMismatchError(DocumentParseError):
    """File content type doesn't match its extension."""


class MaliciousDocumentError(DocumentParseError):
    """Document appears to be malicious (encrypted, macros, etc.)."""


# ── Public API ────────────────────────────────────────────────


async def parse_document(*, file_bytes: bytes, filename: str) -> str:
    """Parse a document and extract text content.

    Runs parsing in a separate thread to avoid blocking the event loop.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used for extension detection).

    Returns:
        Extracted text content.

    Raises:
        FileTooLargeError: If file exceeds MAX_FILE_SIZE.
        UnsupportedFormatError: If extension is not supported.
        MimeMismatchError: If MIME type doesn't match extension.
        MaliciousDocumentError: If document appears malicious.
        DocumentParseError: For any other parsing failure.
    """
    # 1. Size check
    if len(file_bytes) > MAX_FILE_SIZE:
        raise FileTooLargeError(
            f"File size ({len(file_bytes):,} bytes) exceeds limit ({MAX_FILE_SIZE:,} bytes)"
        )

    # 2. Extension check
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported format '{extension}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # 3. MIME verification (skip for .txt — no magic bytes)
    if extension in EXPECTED_MIMES:
        _verify_mime(file_bytes, extension)

    # 4. Dispatch to format-specific parser
    if extension == ".txt":
        return _parse_txt(file_bytes)

    if extension in _IMAGE_EXTENSIONS:
        return await _parse_image(file_bytes, extension)

    return await asyncio.to_thread(_parse_in_thread, file_bytes, extension)


# ── Internal Parsers ──────────────────────────────────────────


async def _parse_image(file_bytes: bytes, extension: str) -> str:
    """Extract text from an image via the OCR service (Claude Vision).

    Args:
        file_bytes: Raw image bytes.
        extension: Lowercase file extension including dot (e.g. ".jpg").

    Returns:
        Extracted text content (may be empty for non-text images).

    Raises:
        DocumentParseError: If the image format is unsupported or OCR fails.
    """
    from app.services.ocr_service import (
        ImageTextExtractionError,
        UnsupportedImageFormatError,
        extract_text_from_image,
        get_image_mime,
    )

    image_mime = get_image_mime(extension)
    if image_mime is None:
        raise UnsupportedFormatError(
            f"No image MIME mapping for '{extension}'"
        )

    try:
        return await extract_text_from_image(
            image_bytes=file_bytes, image_mime=image_mime
        )
    except UnsupportedImageFormatError as exc:
        raise UnsupportedFormatError(str(exc)) from exc
    except ImageTextExtractionError as exc:
        raise DocumentParseError(f"OCR failed: {exc}") from exc


def _verify_mime(file_bytes: bytes, extension: str) -> None:
    """Verify that file content matches expected MIME type."""
    try:
        import filetype
    except ImportError as exc:
        raise DocumentParseError(
            "filetype package not installed. Run: pip install filetype"
        ) from exc

    kind = filetype.guess(file_bytes)
    if kind is None:
        raise MimeMismatchError(
            f"Cannot determine file type for '{extension}' — file may be corrupted"
        )

    expected = EXPECTED_MIMES[extension]
    if kind.mime != expected:
        raise MimeMismatchError(
            f"MIME mismatch: expected '{expected}' for '{extension}', got '{kind.mime}'"
        )


def _parse_txt(file_bytes: bytes) -> str:
    """Parse plain text file with encoding detection."""
    # Try UTF-8 first, fall back to latin-1 (never fails)
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1").strip()


def _parse_in_thread(file_bytes: bytes, extension: str) -> str:
    """Thread-safe document parsing dispatcher."""
    if extension == ".pdf":
        return _parse_pdf(file_bytes)
    if extension == ".docx":
        return _parse_docx(file_bytes)
    raise UnsupportedFormatError(f"No parser for '{extension}'")


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber.

    Guards:
    - Rejects encrypted PDFs
    - Limits to MAX_PAGES pages (memory guard)
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise DocumentParseError(
            "pdfplumber package not installed. Run: pip install pdfplumber"
        ) from exc

    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as exc:
        # pdfplumber raises various exceptions for malformed/encrypted PDFs
        error_msg = str(exc).lower()
        if "password" in error_msg or "encrypt" in error_msg:
            raise MaliciousDocumentError("Encrypted PDFs are not supported") from exc
        raise DocumentParseError(f"Failed to open PDF: {exc}") from exc

    try:
        pages = pdf.pages[:MAX_PAGES]
        if len(pdf.pages) > MAX_PAGES:
            logger.warning(
                "PDF has %d pages, truncating to %d (MAX_PAGES limit)",
                len(pdf.pages),
                MAX_PAGES,
            )

        text_parts: list[str] = []
        for page in pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n\n".join(text_parts).strip()
    finally:
        pdf.close()


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx.

    Guards:
    - Rejects macro-enabled documents (.docm masquerading as .docx)
    """
    try:
        from docx import Document
    except ImportError as exc:
        raise DocumentParseError(
            "python-docx package not installed. Run: pip install python-docx"
        ) from exc

    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        error_msg = str(exc).lower()
        if "macro" in error_msg or "vba" in error_msg:
            raise MaliciousDocumentError(
                "Macro-enabled documents are not supported"
            ) from exc
        raise DocumentParseError(f"Failed to open DOCX: {exc}") from exc

    paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs).strip()
