"""
PathForge — Document Parser Unit Tests
=========================================
Tests for all parsing paths, security guards, and error cases
in app/services/document_parser.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.document_parser import (
    MAX_FILE_SIZE,
    MAX_PAGES,
    DocumentParseError,
    FileTooLargeError,
    MaliciousDocumentError,
    MimeMismatchError,
    UnsupportedFormatError,
    _parse_docx,
    _parse_in_thread,
    _parse_pdf,
    _parse_txt,
    _verify_mime,
    parse_document,
)

# ── Helpers ───────────────────────────────────────────────────

_TXT_BYTES = b"Hello, World!\nLine two."
_BIG_BYTES = b"x" * (MAX_FILE_SIZE + 1)

# Minimal valid PDF magic bytes (%%PDF-1.4 header)
_PDF_MAGIC = b"%PDF-1.4\n"
# Minimal valid DOCX magic bytes (PK ZIP signature)
_DOCX_MAGIC = b"PK\x03\x04"


# ── parse_document: size guard ────────────────────────────────


@pytest.mark.asyncio
async def test_parse_document_too_large() -> None:
    with pytest.raises(FileTooLargeError, match="exceeds limit"):
        await parse_document(file_bytes=_BIG_BYTES, filename="big.txt")


# ── parse_document: extension guard ──────────────────────────


@pytest.mark.asyncio
async def test_parse_document_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
        await parse_document(file_bytes=b"data", filename="resume.xls")


@pytest.mark.asyncio
async def test_parse_document_no_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        await parse_document(file_bytes=b"data", filename="resume")


# ── parse_document: TXT happy path ───────────────────────────


@pytest.mark.asyncio
async def test_parse_document_txt() -> None:
    result = await parse_document(file_bytes=_TXT_BYTES, filename="resume.txt")
    assert "Hello, World!" in result


@pytest.mark.asyncio
async def test_parse_document_txt_uppercase_extension() -> None:
    result = await parse_document(file_bytes=_TXT_BYTES, filename="RESUME.TXT")
    assert "Hello" in result


# ── parse_document: PDF via mime check ───────────────────────


@pytest.mark.asyncio
async def test_parse_document_pdf_happy_path() -> None:
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Software Engineer"

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    mock_kind = MagicMock()
    mock_kind.mime = "application/pdf"

    with patch("filetype.guess", return_value=mock_kind), \
         patch("pdfplumber.open", return_value=mock_pdf):
        result = await parse_document(file_bytes=_PDF_MAGIC, filename="cv.pdf")

    assert "Software Engineer" in result


@pytest.mark.asyncio
async def test_parse_document_pdf_mime_mismatch() -> None:
    mock_kind = MagicMock()
    mock_kind.mime = "image/jpeg"

    with patch("filetype.guess", return_value=mock_kind), \
         pytest.raises(MimeMismatchError, match="MIME mismatch"):
        await parse_document(file_bytes=b"jpeg_data", filename="resume.pdf")


@pytest.mark.asyncio
async def test_parse_document_pdf_unknown_mime() -> None:
    with patch("filetype.guess", return_value=None), \
         pytest.raises(MimeMismatchError, match="Cannot determine"):
        await parse_document(file_bytes=b"garbage", filename="resume.pdf")


# ── parse_document: DOCX via mime check ──────────────────────


@pytest.mark.asyncio
async def test_parse_document_docx_happy_path() -> None:
    mock_para = MagicMock()
    mock_para.text = "My career summary"

    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]

    mock_kind = MagicMock()
    mock_kind.mime = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    with patch("filetype.guess", return_value=mock_kind), \
         patch("docx.Document", return_value=mock_doc):
        result = await parse_document(file_bytes=_DOCX_MAGIC, filename="cv.docx")

    assert "My career summary" in result


@pytest.mark.asyncio
async def test_parse_document_docx_mime_mismatch() -> None:
    mock_kind = MagicMock()
    mock_kind.mime = "application/zip"

    with patch("filetype.guess", return_value=mock_kind), pytest.raises(MimeMismatchError):
        await parse_document(file_bytes=b"zip_data", filename="resume.docx")


# ── _verify_mime ──────────────────────────────────────────────


def test_verify_mime_missing_filetype_package() -> None:
    import builtins

    original_import = builtins.__import__

    def _no_filetype(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "filetype":
            raise ImportError("no module filetype")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_no_filetype), \
         pytest.raises(DocumentParseError, match="filetype package not installed"):
        _verify_mime(b"data", ".pdf")


# ── _parse_txt ────────────────────────────────────────────────


def test_parse_txt_utf8() -> None:
    result = _parse_txt("Héllo Wörld".encode())
    assert "Héllo" in result


def test_parse_txt_latin1_fallback() -> None:
    result = _parse_txt(b"\xe9l\xe8ve")  # latin-1 "élève"
    assert len(result) > 0


def test_parse_txt_strips_whitespace() -> None:
    result = _parse_txt(b"   hello   \n")
    assert result == "hello"


def test_parse_txt_empty() -> None:
    result = _parse_txt(b"   ")
    assert result == ""


# ── _parse_in_thread ──────────────────────────────────────────


def test_parse_in_thread_unsupported() -> None:
    with pytest.raises(UnsupportedFormatError):
        _parse_in_thread(b"data", ".xyz")


def test_parse_in_thread_dispatches_pdf() -> None:
    with patch(
        "app.services.document_parser._parse_pdf", return_value="pdf text"
    ) as mock_pdf:
        result = _parse_in_thread(b"pdf", ".pdf")
    assert result == "pdf text"
    mock_pdf.assert_called_once()


def test_parse_in_thread_dispatches_docx() -> None:
    with patch(
        "app.services.document_parser._parse_docx", return_value="docx text"
    ) as mock_docx:
        result = _parse_in_thread(b"docx", ".docx")
    assert result == "docx text"
    mock_docx.assert_called_once()


# ── _parse_pdf ────────────────────────────────────────────────


def test_parse_pdf_encrypted_raises() -> None:
    with patch("pdfplumber.open", side_effect=Exception("Password required to decrypt")), \
         pytest.raises(MaliciousDocumentError, match="Encrypted"):
        _parse_pdf(b"encrypted_pdf")


def test_parse_pdf_generic_open_error() -> None:
    with patch("pdfplumber.open", side_effect=Exception("corrupt file")), \
         pytest.raises(DocumentParseError, match="Failed to open PDF"):
        _parse_pdf(b"bad_pdf")


def test_parse_pdf_truncates_at_max_pages() -> None:
    pages = [MagicMock() for _ in range(MAX_PAGES + 5)]
    for i, p in enumerate(pages):
        p.extract_text.return_value = f"Page {i}"

    mock_pdf = MagicMock()
    mock_pdf.pages = pages
    mock_pdf.close = MagicMock()
    mock_pdf.__len__ = lambda self: len(pages)

    with patch("pdfplumber.open", return_value=mock_pdf):
        _parse_pdf(b"big_pdf")

    # Only MAX_PAGES pages should be extracted
    assert sum(p.extract_text.call_count for p in pages[:MAX_PAGES]) == MAX_PAGES
    for page in pages[MAX_PAGES:]:
        page.extract_text.assert_not_called()


def test_parse_pdf_skips_empty_pages() -> None:
    page1 = MagicMock()
    page1.extract_text.return_value = "Content"
    page2 = MagicMock()
    page2.extract_text.return_value = None  # empty page

    mock_pdf = MagicMock()
    mock_pdf.pages = [page1, page2]
    mock_pdf.close = MagicMock()

    with patch("pdfplumber.open", return_value=mock_pdf):
        result = _parse_pdf(b"pdf")

    assert result == "Content"


def test_parse_pdf_missing_pdfplumber() -> None:
    import builtins

    original = builtins.__import__

    def _no_pdfplumber(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "pdfplumber":
            raise ImportError("no pdfplumber")
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_no_pdfplumber), \
         pytest.raises(DocumentParseError, match="pdfplumber package"):
        _parse_pdf(b"pdf")


def test_parse_pdf_pdf_close_called_on_success() -> None:
    page = MagicMock()
    page.extract_text.return_value = "text"

    mock_pdf = MagicMock()
    mock_pdf.pages = [page]
    mock_pdf.close = MagicMock()

    with patch("pdfplumber.open", return_value=mock_pdf):
        _parse_pdf(b"pdf")

    mock_pdf.close.assert_called_once()


# ── _parse_docx ───────────────────────────────────────────────


def test_parse_docx_strips_empty_paragraphs() -> None:
    para1 = MagicMock()
    para1.text = "Real content"
    para2 = MagicMock()
    para2.text = "   "  # blank

    mock_doc = MagicMock()
    mock_doc.paragraphs = [para1, para2]

    with patch("docx.Document", return_value=mock_doc):
        result = _parse_docx(b"docx")

    assert result == "Real content"


def test_parse_docx_macro_raises() -> None:
    with patch("docx.Document", side_effect=Exception("vba macros not supported")), \
         pytest.raises(MaliciousDocumentError, match="Macro-enabled"):
        _parse_docx(b"macro_docx")


def test_parse_docx_generic_open_error() -> None:
    with patch("docx.Document", side_effect=Exception("corrupted file")), \
         pytest.raises(DocumentParseError, match="Failed to open DOCX"):
        _parse_docx(b"bad_docx")


def test_parse_docx_missing_python_docx() -> None:
    import builtins

    original = builtins.__import__

    def _no_docx(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "docx":
            raise ImportError("no python-docx")
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_no_docx), \
         pytest.raises(DocumentParseError, match="python-docx"):
        _parse_docx(b"docx")
