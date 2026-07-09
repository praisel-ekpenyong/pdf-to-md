"""Convert a minimal digital PDF without requiring OCR binaries."""

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from pdf_to_md import ConvertOptions, convert_bytes, convert_file
from pdf_to_md.deps import format_dependency_issues, poppler_bin_dir, probe_dependencies
from pdf_to_md.exceptions import ConversionError


def _blank_pdf_bytes() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_convert_bytes_blank_pdf():
    result = convert_bytes(
        _blank_pdf_bytes(),
        ConvertOptions(force_ocr=False, min_chars=20),
        filename="blank.pdf",
    )
    assert result.page_count == 1
    assert "# blank" in result.markdown or "Page 1" in result.markdown
    # Without OCR stack, expect soft warnings rather than a crash
    assert isinstance(result.warnings, list)


def test_convert_file_missing():
    with pytest.raises(ConversionError):
        convert_file(Path("definitely-not-a-real-file-xyz.pdf"))


def test_convert_bytes_empty():
    with pytest.raises(ConversionError):
        convert_bytes(b"")


def test_probe_dependencies_shape():
    report = probe_dependencies()
    assert hasattr(report, "ocr_ready")
    assert hasattr(report, "digital_extract_available")
    msg = format_dependency_issues(report)
    if report.ocr_ready:
        assert msg == ""
    else:
        assert isinstance(msg, str)


def test_poppler_bin_dir():
    assert poppler_bin_dir(None) is None
    assert poppler_bin_dir(r"C:\poppler\Library\bin\pdftoppm.exe") == r"C:\poppler\Library\bin"
