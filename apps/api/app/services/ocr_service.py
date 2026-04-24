"""
PathForge — OCR Service
==========================
AI-powered image-to-text extraction using Claude Vision via LiteLLM.

Supports JPEG, PNG, WebP, and GIF images up to the global file size
limit.  Text is extracted with layout preservation for downstream
resume parsing.

Usage:
    from app.services.ocr_service import extract_text_from_image

    text = await extract_text_from_image(
        image_bytes=content, image_mime="image/jpeg"
    )
"""

from __future__ import annotations

import logging

from app.core.llm import LLMError, LLMTier, complete_vision

logger = logging.getLogger(__name__)

# ── Supported MIME types ──────────────────────────────────────

SUPPORTED_IMAGE_MIMES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
})

# Extension → MIME mapping for image formats
IMAGE_EXTENSION_MIMES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# ── Prompts ───────────────────────────────────────────────────

_OCR_SYSTEM_PROMPT = (
    "You are a precise OCR engine. Your only task is to extract all text "
    "from the provided image, preserving the original structure as closely "
    "as possible. Output only the extracted text — no commentary, no "
    "summaries, no analysis."
)

_OCR_USER_PROMPT = (
    "Extract all text from this image. "
    "Preserve sections, headings, bullet points, and line breaks as they appear. "
    "If the image contains no readable text, output the single word: [EMPTY]"
)

# ── Custom Exceptions ─────────────────────────────────────────


class OCRError(Exception):
    """Base exception for OCR processing failures."""


class UnsupportedImageFormatError(OCRError):
    """Image format is not supported for OCR."""


class ImageTextExtractionError(OCRError):
    """LLM-based text extraction failed."""


# ── Public API ────────────────────────────────────────────────


async def extract_text_from_image(
    *,
    image_bytes: bytes,
    image_mime: str,
) -> str:
    """Extract text from an image using Claude Vision.

    Args:
        image_bytes: Raw bytes of the image.
        image_mime: MIME type of the image (e.g. "image/jpeg").

    Returns:
        Extracted text content. Returns empty string if no text found.

    Raises:
        UnsupportedImageFormatError: If the MIME type is not supported.
        ImageTextExtractionError: If the LLM fails to extract text.
    """
    if image_mime not in SUPPORTED_IMAGE_MIMES:
        raise UnsupportedImageFormatError(
            f"Unsupported image format: '{image_mime}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_MIMES))}"
        )

    logger.info(
        "Starting OCR for %s image (%d bytes)", image_mime, len(image_bytes)
    )

    try:
        raw = await complete_vision(
            image_bytes=image_bytes,
            image_mime=image_mime,
            prompt=_OCR_USER_PROMPT,
            system_prompt=_OCR_SYSTEM_PROMPT,
            tier=LLMTier.FAST,
            temperature=0.0,
            max_tokens=4096,
        )
    except LLMError as exc:
        raise ImageTextExtractionError(
            f"OCR failed for {image_mime} image: {exc}"
        ) from exc

    # Treat explicit empty sentinel as no text
    text = raw.strip()
    if text == "[EMPTY]":
        logger.info("OCR: image contains no readable text")
        return ""

    logger.info(
        "OCR extracted %d characters from %s image", len(text), image_mime
    )
    return text


def get_image_mime(extension: str) -> str | None:
    """Return the MIME type for an image file extension, or None if unsupported.

    Args:
        extension: Lowercase file extension including dot (e.g. ".jpg").

    Returns:
        MIME type string or None.
    """
    return IMAGE_EXTENSION_MIMES.get(extension.lower())
