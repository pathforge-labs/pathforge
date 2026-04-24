"""Tests for app.services.document_parser.

Covers exception hierarchy, size/extension validation, MIME verification,
and format-specific parsers (TXT, PDF, DOCX, image dispatch) with mocks
for external dependencies.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.document_parser import (
    MAX_FILE_SIZE,
    MAX_PAGES,
    SUPPORTED_EXTENSIONS,
    DocumentParseError,
    FileTooLargeError,
    MaliciousDocumentError,
    MimeMismatchError,
    UnsupportedFormatError,
    _parse_docx,
    _parse_image,
    _parse_in_thread,
    _parse_pdf,
    _parse_txt,
    _verify_mime,
    parse_document,
)

# ── Exception Hierarchy ───────────────────────────────────────


def test_file_too_large_subclass_of_document_parse_error() -> None:
    assert issubclass(FileTooLargeError, DocumentParseError)


def test_unsupported_format_subclass_of_document_parse_error() -> None:
    assert issubclass(UnsupportedFormatError, DocumentParseError)


def test_mime_mismatch_subclass_of_document_parse_error() -> None:
    assert issubclass(MimeMismatchError, DocumentParseError)


def test_malicious_document_subclass_of_document_parse_error() -> None:
    assert issubclass(MaliciousDocumentError, DocumentParseError)


def test_document_parse_error_subclass_of_exception() -> None:
    assert issubclass(DocumentParseError, Exception)


# ── Constants ─────────────────────────────────────────────────


def test_supported_extensions_contains_expected() -> None:
    expected = {".txt", ".pdf", ".docx", ".jpg", ".jpeg", ".png", ".webp", ".gif"}
    assert expected == SUPPORTED_EXTENSIONS


def test_max_file_size_is_10mb() -> None:
    assert MAX_FILE_SIZE == 10 * 1024 * 1024


def test_max_pages_is_100() -> None:
    assert MAX_PAGES == 100


# ── parse_document validation ─────────────────────────────────


@pytest.mark.asyncio
async def test_parse_document_rejects_oversized_file() -> None:
    oversized = b"x" * (MAX_FILE_SIZE + 1)
    with pytest.raises(FileTooLargeError):
        await parse_document(file_bytes=oversized, filename="big.txt")


@pytest.mark.asyncio
async def test_parse_document_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        await parse_document(file_bytes=b"data", filename="file.exe")


@pytest.mark.asyncio
async def test_parse_document_rejects_missing_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        await parse_document(file_bytes=b"data", filename="noextension")


@pytest.mark.asyncio
async def test_parse_document_txt_success() -> None:
    content = b"  hello world  "
    result = await parse_document(file_bytes=content, filename="test.txt")
    assert result == "hello world"


# ── TXT parsing ───────────────────────────────────────────────


def test_parse_txt_utf8_decodes_and_strips() -> None:
    assert _parse_txt(b"  hello  ") == "hello"


def test_parse_txt_utf8_unicode_content() -> None:
    assert _parse_txt("café résumé".encode()) == "café résumé"


def test_parse_txt_latin1_fallback() -> None:
    # 0xff is invalid UTF-8 start byte but valid latin-1 (ÿ)
    result = _parse_txt(b"\xffhello")
    assert result == "ÿhello"


def test_parse_txt_empty() -> None:
    assert _parse_txt(b"") == ""


def test_parse_txt_only_whitespace() -> None:
    assert _parse_txt(b"   \n\t  ") == ""


# ── MIME verification ─────────────────────────────────────────


def test_verify_mime_none_raises_mismatch() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = None
    with patch.dict("sys.modules", {"filetype": mock_filetype}), pytest.raises(MimeMismatchError):
        _verify_mime(b"garbage", ".pdf")


def test_verify_mime_wrong_type_raises_mismatch() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(mime="image/png")
    with patch.dict("sys.modules", {"filetype": mock_filetype}), pytest.raises(MimeMismatchError):
        _verify_mime(b"not-a-pdf", ".pdf")


def test_verify_mime_correct_type_passes() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(mime="application/pdf")
    with patch.dict("sys.modules", {"filetype": mock_filetype}):
        # No exception should be raised
        _verify_mime(b"%PDF-1.4", ".pdf")


def test_verify_mime_correct_docx_mime_passes() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    with patch.dict("sys.modules", {"filetype": mock_filetype}):
        _verify_mime(b"PK\x03\x04", ".docx")


def test_verify_mime_raises_when_filetype_not_installed() -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "filetype":
            raise ImportError("No module named 'filetype'")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=fake_import), pytest.raises(DocumentParseError):
        _verify_mime(b"data", ".pdf")


# ── PDF parsing ───────────────────────────────────────────────


def _make_fake_pdf(page_texts: list[str | None]) -> MagicMock:
    """Create a mock pdfplumber PDF object with the given page texts."""
    pages = []
    for text in page_texts:
        page = MagicMock()
        page.extract_text.return_value = text
        pages.append(page)
    pdf = MagicMock()
    pdf.pages = pages
    return pdf


def test_parse_pdf_happy_path_two_pages() -> None:
    fake_pdf = _make_fake_pdf(["Page one content", "Page two content"])
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
        result = _parse_pdf(b"%PDF-1.4 fake")
    assert result == "Page one content\n\nPage two content"


def test_parse_pdf_skips_empty_pages() -> None:
    fake_pdf = _make_fake_pdf(["Real page", None, "", "Another"])
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
        result = _parse_pdf(b"%PDF-1.4")
    assert result == "Real page\n\nAnother"


def test_parse_pdf_encrypted_raises_malicious() -> None:
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.side_effect = Exception("PDF requires a password to open")
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}), pytest.raises(MaliciousDocumentError):
        _parse_pdf(b"encrypted pdf bytes")


def test_parse_pdf_encrypt_keyword_raises_malicious() -> None:
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.side_effect = Exception("File is encrypted")
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}), pytest.raises(MaliciousDocumentError):
        _parse_pdf(b"encrypted bytes")


def test_parse_pdf_corrupt_raises_document_parse_error() -> None:
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.side_effect = Exception("Malformed xref table")
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}), pytest.raises(DocumentParseError) as exc_info:
        _parse_pdf(b"garbage pdf")
    assert not isinstance(exc_info.value, MaliciousDocumentError)


def test_parse_pdf_truncates_to_max_pages() -> None:
    texts: list[str | None] = [f"Page {i}" for i in range(MAX_PAGES + 10)]
    fake_pdf = _make_fake_pdf(texts)
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
        result = _parse_pdf(b"%PDF")
    # Last included page should be Page {MAX_PAGES - 1}
    assert f"Page {MAX_PAGES - 1}" in result
    assert f"Page {MAX_PAGES}" not in result


def test_parse_pdf_close_called_even_on_extraction_failure() -> None:
    fake_pdf = MagicMock()
    page = MagicMock()
    page.extract_text.side_effect = RuntimeError("extraction boom")
    fake_pdf.pages = [page]
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}), pytest.raises(RuntimeError):
        _parse_pdf(b"%PDF")
    fake_pdf.close.assert_called_once()


def test_parse_pdf_close_called_on_success() -> None:
    fake_pdf = _make_fake_pdf(["hello"])
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
        _parse_pdf(b"%PDF")
    fake_pdf.close.assert_called_once()


def test_parse_pdf_raises_when_pdfplumber_not_installed() -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pdfplumber":
            raise ImportError("No module named 'pdfplumber'")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=fake_import), pytest.raises(DocumentParseError):
        _parse_pdf(b"%PDF")


# ── DOCX parsing ──────────────────────────────────────────────


def _make_fake_docx(paragraph_texts: list[str]) -> MagicMock:
    paragraphs = []
    for text in paragraph_texts:
        p = MagicMock()
        p.text = text
        paragraphs.append(p)
    doc = MagicMock()
    doc.paragraphs = paragraphs
    return doc


def test_parse_docx_happy_path() -> None:
    fake_doc = _make_fake_docx(["First paragraph", "Second paragraph"])
    mock_docx_module = MagicMock()
    mock_docx_module.Document.return_value = fake_doc
    with patch.dict("sys.modules", {"docx": mock_docx_module}):
        result = _parse_docx(b"PK\x03\x04 docx")
    assert result == "First paragraph\n\nSecond paragraph"


def test_parse_docx_filters_empty_paragraphs() -> None:
    fake_doc = _make_fake_docx(["Real", "   ", "", "Another"])
    mock_docx_module = MagicMock()
    mock_docx_module.Document.return_value = fake_doc
    with patch.dict("sys.modules", {"docx": mock_docx_module}):
        result = _parse_docx(b"PK")
    assert result == "Real\n\nAnother"


def test_parse_docx_macro_raises_malicious() -> None:
    mock_docx_module = MagicMock()
    mock_docx_module.Document.side_effect = Exception("Document contains macro VBA project")
    with patch.dict("sys.modules", {"docx": mock_docx_module}), pytest.raises(MaliciousDocumentError):
        _parse_docx(b"malicious")


def test_parse_docx_vba_raises_malicious() -> None:
    mock_docx_module = MagicMock()
    mock_docx_module.Document.side_effect = Exception("VBA payload detected")
    with patch.dict("sys.modules", {"docx": mock_docx_module}), pytest.raises(MaliciousDocumentError):
        _parse_docx(b"malicious")


def test_parse_docx_failed_open_raises_document_parse_error() -> None:
    mock_docx_module = MagicMock()
    mock_docx_module.Document.side_effect = Exception("Not a zip file")
    with patch.dict("sys.modules", {"docx": mock_docx_module}), pytest.raises(DocumentParseError) as exc_info:
        _parse_docx(b"garbage")
    assert not isinstance(exc_info.value, MaliciousDocumentError)


def test_parse_docx_raises_when_python_docx_not_installed() -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "docx":
            raise ImportError("No module named 'docx'")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=fake_import), pytest.raises(DocumentParseError):
        _parse_docx(b"PK")


# ── Dispatcher ────────────────────────────────────────────────


def test_parse_in_thread_unknown_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        _parse_in_thread(b"data", ".unknown")


def test_parse_in_thread_dispatches_pdf() -> None:
    fake_pdf = _make_fake_pdf(["dispatched"])
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
        result = _parse_in_thread(b"%PDF", ".pdf")
    assert result == "dispatched"


def test_parse_in_thread_dispatches_docx() -> None:
    fake_doc = _make_fake_docx(["dispatched"])
    mock_docx_module = MagicMock()
    mock_docx_module.Document.return_value = fake_doc
    with patch.dict("sys.modules", {"docx": mock_docx_module}):
        result = _parse_in_thread(b"PK", ".docx")
    assert result == "dispatched"


# ── Image dispatch ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_document_jpg_dispatches_to_image_parser() -> None:
    mock_extract = AsyncMock(return_value="ocr text")
    mock_get_mime = MagicMock(return_value="image/jpeg")
    with (
        patch("app.services.document_parser.extract_text_from_image", new=mock_extract),
        patch("app.services.document_parser.get_image_mime", new=mock_get_mime),
    ):
        result = await parse_document(file_bytes=b"\xff\xd8\xff fake jpg", filename="photo.jpg")
    assert result == "ocr text"
    mock_extract.assert_awaited_once()
    mock_get_mime.assert_called_once_with(".jpg")


@pytest.mark.asyncio
async def test_parse_image_maps_extension_to_mime() -> None:
    mock_extract = AsyncMock(return_value="png text")
    mock_get_mime = MagicMock(return_value="image/png")
    with (
        patch("app.services.document_parser.extract_text_from_image", new=mock_extract),
        patch("app.services.document_parser.get_image_mime", new=mock_get_mime),
    ):
        result = await _parse_image(b"png bytes", ".png")
    assert result == "png text"
    mock_extract.assert_awaited_once_with(image_bytes=b"png bytes", image_mime="image/png")


@pytest.mark.asyncio
async def test_parse_image_unknown_mime_raises_unsupported() -> None:
    with (
        patch("app.services.document_parser.get_image_mime", return_value=None),
        patch("app.services.document_parser.extract_text_from_image", new=AsyncMock()),
        pytest.raises(UnsupportedFormatError),
    ):
        await _parse_image(b"bytes", ".bmp")


@pytest.mark.asyncio
async def test_parse_image_unsupported_image_format_error_reraised() -> None:
    from app.services.ocr_service import UnsupportedImageFormatError as RealUnsupportedImageFormatError

    with (
        patch("app.services.document_parser.get_image_mime", return_value="image/webp"),
        patch(
            "app.services.document_parser.extract_text_from_image",
            new=AsyncMock(side_effect=RealUnsupportedImageFormatError("bad image")),
        ),
        pytest.raises(UnsupportedFormatError),
    ):
        await _parse_image(b"bytes", ".webp")


@pytest.mark.asyncio
async def test_parse_image_text_extraction_error_reraised_as_parse_error() -> None:
    from app.services.ocr_service import ImageTextExtractionError as RealImageTextExtractionError

    with (
        patch("app.services.document_parser.get_image_mime", return_value="image/gif"),
        patch(
            "app.services.document_parser.extract_text_from_image",
            new=AsyncMock(side_effect=RealImageTextExtractionError("OCR broke")),
        ),
        pytest.raises(DocumentParseError) as exc_info,
    ):
        await _parse_image(b"bytes", ".gif")
    assert not isinstance(exc_info.value, UnsupportedFormatError)


# ── parse_document end-to-end flows ───────────────────────────


@pytest.mark.asyncio
async def test_parse_document_pdf_with_mime_check_and_parsing() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(mime="application/pdf")
    fake_pdf = _make_fake_pdf(["extracted pdf text"])
    mock_pdfplumber = MagicMock()
    mock_pdfplumber.open.return_value = fake_pdf
    with patch.dict("sys.modules", {"filetype": mock_filetype, "pdfplumber": mock_pdfplumber}):
        result = await parse_document(file_bytes=b"%PDF-1.4 fake", filename="resume.pdf")
    assert result == "extracted pdf text"


@pytest.mark.asyncio
async def test_parse_document_docx_with_mime_check_and_parsing() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    fake_doc = _make_fake_docx(["docx content"])
    mock_docx_module = MagicMock()
    mock_docx_module.Document.return_value = fake_doc
    with patch.dict("sys.modules", {"filetype": mock_filetype, "docx": mock_docx_module}):
        result = await parse_document(file_bytes=b"PK\x03\x04", filename="resume.docx")
    assert result == "docx content"


@pytest.mark.asyncio
async def test_parse_document_pdf_mime_mismatch_raises() -> None:
    mock_filetype = MagicMock()
    mock_filetype.guess.return_value = SimpleNamespace(mime="image/png")
    with patch.dict("sys.modules", {"filetype": mock_filetype}), pytest.raises(MimeMismatchError):
        await parse_document(file_bytes=b"not a pdf", filename="resume.pdf")
