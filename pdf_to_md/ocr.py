"""OCR via pdf2image + Tesseract."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

try:
    import pytesseract
    from pdf2image import convert_from_path

    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False
    pytesseract = None  # type: ignore
    convert_from_path = None  # type: ignore

ProgressCb = Callable[[int, int, str], None]  # current (1-based), total, message


def ocr_available() -> bool:
    """True if Python OCR packages import successfully.

    Does not guarantee Tesseract/Poppler binaries are installed.
    """
    return _OCR_AVAILABLE


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if tesseract_cmd and pytesseract is not None:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


class OcrRuntimeError(Exception):
    """Raised when OCR binaries fail at runtime (poppler/tesseract)."""


def _resolve_poppler_bin_dir(poppler_path: str | None) -> str | None:
    """Accept either pdftoppm executable path or its bin directory."""
    if not poppler_path:
        return None
    from pdf_to_md.deps import poppler_bin_dir

    return poppler_bin_dir(poppler_path)


def ocr_page_indices(
    pdf_path: Path,
    page_indices: list[int],
    *,
    dpi: int = 300,
    lang: str = "eng",
    progress: ProgressCb | None = None,
    raise_on_failure: bool = False,
    poppler_path: str | None = None,
) -> tuple[list[str], list[str]]:
    """OCR specific 0-based page indices.

    *poppler_path* may be the path to ``pdftoppm`` or its containing directory.

    Returns (texts aligned with page_indices, warnings).
    """
    warnings: list[str] = []
    if not page_indices:
        return [], warnings

    if not _OCR_AVAILABLE:
        msg = (
            "OCR requested but pytesseract/pdf2image not installed. "
            "pip install pytesseract pdf2image pillow; install Tesseract + Poppler."
        )
        print(f"  [warn] {msg}", file=sys.stderr)
        warnings.append(msg)
        if raise_on_failure:
            raise OcrRuntimeError(msg)
        return [""] * len(page_indices), warnings

    poppler_dir = _resolve_poppler_bin_dir(poppler_path)
    convert_kwargs: dict = {"dpi": dpi}
    if poppler_dir:
        convert_kwargs["poppler_path"] = poppler_dir

    total = len(page_indices)
    results: dict[int, str] = {}

    for n, idx in enumerate(page_indices, start=1):
        page_no = idx + 1
        if progress:
            progress(n, total, f"OCR page {page_no} ({n}/{total})")
        try:
            images = convert_from_path(
                str(pdf_path),
                first_page=page_no,
                last_page=page_no,
                **convert_kwargs,
            )
        except Exception as exc:
            msg = (
                f"pdf2image failed on page {page_no}: {exc}. "
                "Is Poppler installed and on PATH? (pdftoppm)"
            )
            print(f"  [warn] {msg}", file=sys.stderr)
            warnings.append(msg)
            if raise_on_failure:
                raise OcrRuntimeError(msg) from exc
            results[idx] = ""
            continue

        if not images:
            msg = f"No image rendered for page {page_no} (Poppler may be misconfigured)."
            warnings.append(msg)
            results[idx] = ""
            continue

        try:
            results[idx] = pytesseract.image_to_string(images[0], lang=lang)
        except Exception as exc:  # pragma: no cover
            msg = (
                f"Tesseract failed on page {page_no}: {exc}. "
                "Is Tesseract installed and on PATH?"
            )
            print(f"  [warn] {msg}", file=sys.stderr)
            warnings.append(msg)
            if raise_on_failure:
                raise OcrRuntimeError(msg) from exc
            results[idx] = ""

    return [results.get(i, "") for i in page_indices], warnings
