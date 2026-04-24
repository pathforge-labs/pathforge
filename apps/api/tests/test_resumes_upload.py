"""
PathForge — Resume Upload Endpoint Tests
==========================================
Integration tests for POST /api/v1/resumes/upload and GET /api/v1/resumes/.
Uses in-memory SQLite + AsyncClient; document parsing and LLM calls are mocked.
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

_PARSE_DOC_PATH = "app.services.document_parser.parse_document"
_RESUME_PARSER_PATH = "app.ai.resume_parser.ResumeParser"

_PDF_BYTES = b"%PDF-1.4 fake"
_TXT_BYTES = b"John Doe\nSoftware Engineer"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
_PNG_BYTES = b"\x89PNG" + b"\x00" * 100


# ── Helpers ───────────────────────────────────────────────────

def _txt_file(content: bytes = _TXT_BYTES, filename: str = "cv.txt") -> dict[str, Any]:
    return {"file": (filename, io.BytesIO(content), "text/plain")}


def _pdf_file(content: bytes = _PDF_BYTES, filename: str = "cv.pdf") -> dict[str, Any]:
    return {"file": (filename, io.BytesIO(content), "application/pdf")}


def _jpg_file(content: bytes = _JPEG_BYTES, filename: str = "cv.jpg") -> dict[str, Any]:
    return {"file": (filename, io.BytesIO(content), "image/jpeg")}


def _png_file(content: bytes = _PNG_BYTES, filename: str = "cv.png") -> dict[str, Any]:
    return {"file": (filename, io.BytesIO(content), "image/png")}


# ── POST /resumes/upload — authentication guard ───────────────


@pytest.mark.asyncio
async def test_upload_requires_auth(client: Any) -> None:
    response = await client.post("/api/v1/resumes/upload", files=_txt_file())
    assert response.status_code == 401


# ── POST /resumes/upload — validation errors ──────────────────


@pytest.mark.asyncio
async def test_upload_no_filename_rejected(client: Any, auth_headers: dict[str, str]) -> None:
    """UploadFile with empty filename should return 422."""
    response = await client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers,
        files={"file": ("", io.BytesIO(b"data"), "text/plain")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_unsupported_extension_rejected(
    client: Any, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.bmp", io.BytesIO(b"data"), "image/bmp")},
    )
    assert response.status_code == 422
    body = response.json()
    assert ".bmp" in body["detail"]


@pytest.mark.asyncio
async def test_upload_empty_text_rejected(client: Any, auth_headers: dict[str, str]) -> None:
    with patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="   "):
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )
    assert response.status_code == 422
    assert "No text" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large_returns_413(
    client: Any, auth_headers: dict[str, str]
) -> None:
    from app.services.document_parser import FileTooLargeError

    with patch(_PARSE_DOC_PATH, new_callable=AsyncMock, side_effect=FileTooLargeError("too big")):
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_unsupported_format_error_returns_422(
    client: Any, auth_headers: dict[str, str]
) -> None:
    from app.services.document_parser import UnsupportedFormatError

    with patch(
        _PARSE_DOC_PATH,
        new_callable=AsyncMock,
        side_effect=UnsupportedFormatError("bad format"),
    ):
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_document_parse_error_returns_422(
    client: Any, auth_headers: dict[str, str]
) -> None:
    from app.services.document_parser import DocumentParseError

    with patch(
        _PARSE_DOC_PATH,
        new_callable=AsyncMock,
        side_effect=DocumentParseError("corrupt"),
    ):
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )
    assert response.status_code == 422
    assert "Could not parse document" in response.json()["detail"]


# ── POST /resumes/upload — happy paths ────────────────────────


@pytest.mark.asyncio
async def test_upload_txt_success(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="John Doe\nDeveloper"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(
            return_value={"name": "John Doe", "title": "Developer"}
        )
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["resume_id"]
    assert body["version"] == 1
    assert body["raw_text_length"] == len("John Doe\nDeveloper")
    assert body["ocr_used"] is False
    assert "uploaded and parsed" in body["message"]


@pytest.mark.asyncio
async def test_upload_pdf_success(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="Resume text from PDF"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={"name": "Jane"})
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_pdf_file(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["ocr_used"] is False
    assert body["structured_data"] == {"name": "Jane"}


@pytest.mark.asyncio
async def test_upload_jpeg_sets_ocr_used(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="OCR extracted text"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={"name": "Scan"})
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_jpg_file(),
        )

    assert response.status_code == 201
    assert response.json()["ocr_used"] is True


@pytest.mark.asyncio
async def test_upload_png_sets_ocr_used(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="PNG OCR text"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={})
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_png_file(),
        )

    assert response.status_code == 201
    assert response.json()["ocr_used"] is True


@pytest.mark.asyncio
async def test_upload_webp_sets_ocr_used(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="WebP OCR text"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={})
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files={"file": ("cv.webp", io.BytesIO(b"RIFF"), "image/webp")},
        )

    assert response.status_code == 201
    assert response.json()["ocr_used"] is True


@pytest.mark.asyncio
async def test_upload_gif_sets_ocr_used(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="GIF OCR text"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={})
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files={"file": ("cv.gif", io.BytesIO(b"GIF89a"), "image/gif")},
        )

    assert response.status_code == 201
    assert response.json()["ocr_used"] is True


# ── POST /resumes/upload — structured parsing optional ────────


@pytest.mark.asyncio
async def test_upload_without_structured_parsing(
    client: Any, auth_headers: dict[str, str]
) -> None:
    with patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="Raw resume text"):
        response = await client.post(
            "/api/v1/resumes/upload?parse_structured=false",
            headers=auth_headers,
            files=_txt_file(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["structured_data"] is None
    assert "Text extracted" in body["message"]


@pytest.mark.asyncio
async def test_upload_llm_parse_failure_gracefully_degrades(
    client: Any, auth_headers: dict[str, str]
) -> None:
    """LLM parse failure should not fail the request — saves raw text only."""
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="Resume content"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(side_effect=Exception("LLM timeout"))
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["structured_data"] is None
    assert "Text extracted" in body["message"]


# ── POST /resumes/upload — version increment ──────────────────


@pytest.mark.asyncio
async def test_upload_increments_version(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="First resume"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={"v": 1})
        r1 = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(filename="cv1.txt"),
        )

    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="Second resume"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={"v": 2})
        r2 = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(filename="cv2.txt"),
        )

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["version"] == 1
    assert r2.json()["version"] == 2


# ── POST /resumes/upload — structured_data from pydantic model ─


@pytest.mark.asyncio
async def test_upload_structured_data_from_pydantic_model(
    client: Any, auth_headers: dict[str, str]
) -> None:
    """If ResumeParser returns a Pydantic model, model_dump() should be used."""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"name": "From Pydantic", "skills": ["Python"]}

    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="Resume text"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value=mock_result)
        response = await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["structured_data"] == {"name": "From Pydantic", "skills": ["Python"]}


# ── GET /resumes/ ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_resumes_requires_auth(client: Any) -> None:
    response = await client.get("/api/v1/resumes/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_resumes_empty(client: Any, auth_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/resumes/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_resumes_returns_uploaded(client: Any, auth_headers: dict[str, str]) -> None:
    with (
        patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value="My resume content"),
        patch(_RESUME_PARSER_PATH) as mock_parser_cls,
    ):
        mock_parser_cls.return_value.parse = AsyncMock(return_value={"name": "Me"})
        await client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=_txt_file(),
        )

    response = await client.get("/api/v1/resumes/", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    item = items[0]
    assert "id" in item
    assert "title" in item
    assert "version" in item
    assert "raw_text_length" in item
    assert "has_structured_data" in item
    assert "has_embedding" in item
    assert "created_at" in item


@pytest.mark.asyncio
async def test_list_resumes_newest_first(client: Any, auth_headers: dict[str, str]) -> None:
    for i in range(3):
        with (
            patch(_PARSE_DOC_PATH, new_callable=AsyncMock, return_value=f"Resume {i}"),
            patch(_RESUME_PARSER_PATH) as mock_parser_cls,
        ):
            mock_parser_cls.return_value.parse = AsyncMock(return_value={})
            await client.post(
                "/api/v1/resumes/upload",
                headers=auth_headers,
                files=_txt_file(filename=f"cv{i}.txt"),
            )

    response = await client.get("/api/v1/resumes/", headers=auth_headers)
    items = response.json()
    versions = [item["version"] for item in items]
    assert versions == sorted(versions, reverse=True)
