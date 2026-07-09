"""Digital text extraction from PDFs."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    from pypdf import PdfReader as _PyPdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader as _PyPdfReader  # type: ignore
    except ImportError:  # pragma: no cover
        _PyPdfReader = None


def page_count(pdf_path: Path) -> int:
    """Return number of pages, preferring pdfplumber then pypdf."""
    if pdfplumber is not None:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                return len(pdf.pages)
        except Exception:
            pass
    if _PyPdfReader is not None:
        try:
            return len(_PyPdfReader(str(pdf_path)).pages)
        except Exception:
            pass
    return 0


def extract_text_pages(pdf_path: Path) -> list[str]:
    """Extract text per page. Tries pdfplumber, falls back to pypdf.

    Returns a list of strings, one per page (may be empty strings).
    """
    pages = _extract_pdfplumber(pdf_path)
    if pages and any(p.strip() for p in pages):
        return pages

    pypdf_pages = _extract_pypdf(pdf_path)
    if pypdf_pages and any(p.strip() for p in pypdf_pages):
        return pypdf_pages

    # Prefer non-empty structure: use whichever has page count, else empty.
    if pages:
        return pages
    if pypdf_pages:
        return pypdf_pages

    n = page_count(pdf_path)
    return [""] * n if n else []


def _extract_pdfplumber(pdf_path: Path) -> list[str]:
    if pdfplumber is None:
        return []
    pages: list[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception as exc:  # pragma: no cover
                    print(f"  [warn] pdfplumber page failed: {exc}", file=sys.stderr)
                    pages.append("")
    except Exception as exc:
        print(f"  [warn] pdfplumber open failed: {exc}", file=sys.stderr)
    return pages


def _extract_pypdf(pdf_path: Path) -> list[str]:
    if _PyPdfReader is None:
        return []
    try:
        reader = _PyPdfReader(str(pdf_path))
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # pragma: no cover
        print(f"  [warn] pypdf failed: {exc}", file=sys.stderr)
        return []


def digital_stack_available() -> bool:
    return pdfplumber is not None or _PyPdfReader is not None
