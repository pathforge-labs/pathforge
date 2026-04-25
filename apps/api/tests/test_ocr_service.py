"""
PathForge — OCR Service Unit Tests
=====================================
Tests for image-to-text extraction in app/services/ocr_service.py.
LLM Vision calls are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ocr_service import (
    IMAGE_EXTENSION_MIMES,
    SUPPORTED_IMAGE_MIMES,
    ImageTextExtractionError,
    OCRError,
    UnsupportedImageFormatError,
    extract_text_from_image,
    get_image_mime,
)

VISION_PATH = "app.services.ocr_service.complete_vision"

_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header

# ── get_image_mime ────────────────────────────────────────────


def test_get_image_mime_jpeg() -> None:
    assert get_image_mime(".jpg") == "image/jpeg"
    assert get_image_mime(".jpeg") == "image/jpeg"


def test_get_image_mime_png() -> None:
    assert get_image_mime(".png") == "image/png"


def test_get_image_mime_webp() -> None:
    assert get_image_mime(".webp") == "image/webp"


def test_get_image_mime_gif() -> None:
    assert get_image_mime(".gif") == "image/gif"


def test_get_image_mime_unknown_returns_none() -> None:
    assert get_image_mime(".bmp") is None
    assert get_image_mime(".tiff") is None
    assert get_image_mime("") is None


def test_get_image_mime_case_insensitive() -> None:
    assert get_image_mime(".JPG") == "image/jpeg"
    assert get_image_mime(".PNG") == "image/png"


# ── SUPPORTED_IMAGE_MIMES ────────────────────────────────────


def test_supported_image_mimes_contains_common_formats() -> None:
    assert "image/jpeg" in SUPPORTED_IMAGE_MIMES
    assert "image/png" in SUPPORTED_IMAGE_MIMES
    assert "image/webp" in SUPPORTED_IMAGE_MIMES
    assert "image/gif" in SUPPORTED_IMAGE_MIMES


def test_extension_mime_mapping_consistent() -> None:
    for ext, mime in IMAGE_EXTENSION_MIMES.items():
        assert mime in SUPPORTED_IMAGE_MIMES, (
            f"{ext} maps to {mime} which is not in SUPPORTED_IMAGE_MIMES"
        )


# ── extract_text_from_image: validation ──────────────────────


@pytest.mark.asyncio
async def test_unsupported_mime_raises() -> None:
    with pytest.raises(UnsupportedImageFormatError, match="Unsupported image format"):
        await extract_text_from_image(
            image_bytes=b"data", image_mime="image/bmp"
        )


@pytest.mark.asyncio
async def test_unsupported_mime_is_ocr_error() -> None:
    with pytest.raises(OCRError):
        await extract_text_from_image(
            image_bytes=b"data", image_mime="application/pdf"
        )


# ── extract_text_from_image: happy paths ─────────────────────


@pytest.mark.asyncio
async def test_extract_text_jpeg_happy_path() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="John Doe\nSoftware Engineer"):
        result = await extract_text_from_image(
            image_bytes=_JPEG_BYTES, image_mime="image/jpeg"
        )
    assert "John Doe" in result
    assert "Software Engineer" in result


@pytest.mark.asyncio
async def test_extract_text_png_happy_path() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="Python Developer"):
        result = await extract_text_from_image(
            image_bytes=b"\x89PNG", image_mime="image/png"
        )
    assert "Python Developer" in result


@pytest.mark.asyncio
async def test_extract_text_webp_happy_path() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="WebP text"):
        result = await extract_text_from_image(
            image_bytes=b"RIFF", image_mime="image/webp"
        )
    assert result == "WebP text"


@pytest.mark.asyncio
async def test_extract_text_gif_happy_path() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="GIF text"):
        result = await extract_text_from_image(
            image_bytes=b"GIF89a", image_mime="image/gif"
        )
    assert result == "GIF text"


# ── extract_text_from_image: empty sentinel ───────────────────


@pytest.mark.asyncio
async def test_empty_image_returns_empty_string() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="[EMPTY]"):
        result = await extract_text_from_image(
            image_bytes=b"data", image_mime="image/jpeg"
        )
    assert result == ""


@pytest.mark.asyncio
async def test_empty_sentinel_with_whitespace() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="  [EMPTY]  "):
        result = await extract_text_from_image(
            image_bytes=b"data", image_mime="image/jpeg"
        )
    assert result == ""


# ── extract_text_from_image: response stripping ──────────────


@pytest.mark.asyncio
async def test_response_is_stripped() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="  text  \n"):
        result = await extract_text_from_image(
            image_bytes=b"data", image_mime="image/jpeg"
        )
    assert result == "text"


# ── extract_text_from_image: LLM error handling ───────────────


@pytest.mark.asyncio
async def test_llm_error_raises_image_text_extraction_error() -> None:
    from app.core.llm import LLMError

    with patch(VISION_PATH, new_callable=AsyncMock, side_effect=LLMError("timeout")), pytest.raises(ImageTextExtractionError, match="OCR failed"):
        await extract_text_from_image(
            image_bytes=b"data", image_mime="image/jpeg"
        )


@pytest.mark.asyncio
async def test_image_text_extraction_error_is_ocr_error() -> None:
    from app.core.llm import LLMError

    with patch(VISION_PATH, new_callable=AsyncMock, side_effect=LLMError("x")), pytest.raises(OCRError):
        await extract_text_from_image(
            image_bytes=b"data", image_mime="image/png"
        )


# ── extract_text_from_image: vision call parameters ──────────


@pytest.mark.asyncio
async def test_calls_complete_vision_with_correct_mime() -> None:
    with patch(VISION_PATH, new_callable=AsyncMock, return_value="text") as mock_vision:
        await extract_text_from_image(
            image_bytes=_JPEG_BYTES, image_mime="image/jpeg"
        )

    call_kwargs = mock_vision.call_args.kwargs
    assert call_kwargs["image_mime"] == "image/jpeg"
    assert call_kwargs["image_bytes"] == _JPEG_BYTES
    assert call_kwargs["temperature"] == 0.0


@pytest.mark.asyncio
async def test_calls_complete_vision_fast_tier() -> None:
    from app.core.llm import LLMTier

    with patch(VISION_PATH, new_callable=AsyncMock, return_value="text") as mock_vision:
        await extract_text_from_image(
            image_bytes=b"data", image_mime="image/png"
        )

    call_kwargs = mock_vision.call_args.kwargs
    assert call_kwargs["tier"] == LLMTier.FAST
