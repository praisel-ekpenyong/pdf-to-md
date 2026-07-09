"""High-level conversion API for files and in-memory PDF bytes."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pdf_to_md.exceptions import ConversionError, MissingDependencyError
from pdf_to_md.extract import digital_stack_available, extract_text_pages
from pdf_to_md.images import extract_images
from pdf_to_md.markdown import build_markdown
from pdf_to_md.ocr import OcrRuntimeError, configure_tesseract, ocr_available, ocr_page_indices

DEFAULT_MIN_CHARS = 20
# Soft local safeguard: warn only (does not abort conversion)
SOFT_PAGE_WARN_THRESHOLD = 100

ProgressCb = Callable[[int, int, str], None]  # current, total, message


@dataclass
class ConvertOptions:
    """Options controlling hybrid text extraction and OCR."""

    lang: str = "eng"
    ocr_dpi: int = 300
    force_ocr: bool = False
    min_chars: int = DEFAULT_MIN_CHARS
    extract_images: bool = False
    tesseract_cmd: str | None = None
    image_output_dir: Path | str | None = None
    title: str | None = None
    # When True, OCR binary failures raise instead of soft-empty pages
    strict_ocr: bool = False
    # Soft warning only when page count exceeds this (None = use default threshold)
    page_warn_threshold: int | None = SOFT_PAGE_WARN_THRESHOLD


@dataclass
class ConvertResult:
    """Result of a PDF → Markdown conversion."""

    markdown: str
    page_count: int
    ocr_pages: list[int] = field(default_factory=list)  # 1-based
    images: dict[int, list[str]] = field(default_factory=dict)  # 0-based page → names
    source_name: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "markdown": self.markdown,
            "page_count": self.page_count,
            "ocr_pages": self.ocr_pages,
            "images": {str(k): v for k, v in self.images.items()},
            "source_name": self.source_name,
            "warnings": self.warnings,
        }


def convert_file(
    pdf_path: Path | str,
    options: ConvertOptions | None = None,
    *,
    progress: ProgressCb | None = None,
) -> ConvertResult:
    """Convert a PDF on disk to Markdown.

    *progress* is called as progress(current, total, message) during OCR.
    """
    options = options or ConvertOptions()
    path = Path(pdf_path)
    warnings: list[str] = []

    if not path.is_file():
        raise ConversionError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ConversionError(f"Expected a .pdf file, got: {path.name}")

    if not digital_stack_available() and not options.force_ocr:
        raise MissingDependencyError(
            "Install pdfplumber or pypdf for digital text extraction "
            "(or use force_ocr=True with OCR dependencies)."
        )

    # Prefer explicit cmd; otherwise probe may discover a Windows install path
    configure_tesseract(options.tesseract_cmd)

    if progress:
        progress(0, 1, "Extracting digital text…")

    try:
        text_pages = extract_text_pages(path)
    except Exception as exc:
        raise ConversionError(f"Failed to read PDF: {exc}") from exc

    if not text_pages and options.force_ocr:
        text_pages = [""]

    threshold = options.page_warn_threshold
    if threshold is not None and len(text_pages) > threshold:
        warnings.append(
            f"Large PDF ({len(text_pages)} pages). OCR may use a lot of CPU/RAM; "
            "consider converting fewer pages or lowering --ocr-dpi."
        )

    if options.force_ocr:
        ocr_indices = list(range(len(text_pages)))
    else:
        ocr_indices = [
            i
            for i, t in enumerate(text_pages)
            if len((t or "").strip()) < options.min_chars
        ]

    ocr_pages_1based: list[int] = []
    if ocr_indices:
        if not ocr_available():
            msg = (
                "OCR needed for some pages but pytesseract/pdf2image are not installed. "
                "pip install pytesseract pdf2image pillow; install Tesseract + Poppler."
            )
            warnings.append(msg)
            if options.force_ocr or options.strict_ocr:
                raise MissingDependencyError(msg)
        else:
            from pdf_to_md.deps import format_dependency_issues, probe_dependencies

            # Single probe for readiness + poppler/tesseract paths
            report = probe_dependencies(options.tesseract_cmd)
            if report.tesseract_available and report.tesseract_path and not options.tesseract_cmd:
                configure_tesseract(report.tesseract_path)

            if not report.ocr_ready:
                detail = format_dependency_issues(report)
                warnings.append(detail)
                if options.force_ocr or options.strict_ocr:
                    raise MissingDependencyError(
                        "OCR required but system dependencies are incomplete.\n" + detail
                    )
            else:

                def _ocr_progress(cur: int, tot: int, msg: str) -> None:
                    if progress:
                        progress(cur, tot, msg)

                try:
                    ocr_texts, ocr_warnings = ocr_page_indices(
                        path,
                        ocr_indices,
                        dpi=options.ocr_dpi,
                        lang=options.lang,
                        progress=_ocr_progress,
                        raise_on_failure=options.force_ocr or options.strict_ocr,
                        poppler_path=report.poppler_path,
                    )
                except OcrRuntimeError as exc:
                    raise MissingDependencyError(str(exc)) from exc

                warnings.extend(ocr_warnings)
                for idx, ocr_text in zip(ocr_indices, ocr_texts):
                    if options.force_ocr or len((text_pages[idx] or "").strip()) < options.min_chars:
                        text_pages[idx] = ocr_text
                        ocr_pages_1based.append(idx + 1)

                if ocr_indices and not any((t or "").strip() for t in ocr_texts):
                    warnings.append(
                        "OCR ran but recovered no text. Check Tesseract language packs "
                        f"(lang={options.lang}) and Poppler rendering."
                    )

    image_map: dict[int, list[str]] = {}
    image_dir_name = ""
    if options.extract_images:
        if progress:
            progress(0, 1, "Extracting images…")
        if options.image_output_dir is not None:
            image_dir = Path(options.image_output_dir)
        else:
            image_dir = path.parent / f"{path.stem}_images"
        image_map = extract_images(path, image_dir, path.stem)
        image_dir_name = image_dir.name

    title = options.title or path.stem
    md = build_markdown(
        text_pages,
        image_map,
        title=title,
        image_dir_name=image_dir_name,
    )

    if progress:
        progress(1, 1, "Done")

    return ConvertResult(
        markdown=md,
        page_count=len(text_pages),
        ocr_pages=ocr_pages_1based,
        images=image_map,
        source_name=path.name,
        warnings=warnings,
    )


def convert_bytes(
    data: bytes,
    options: ConvertOptions | None = None,
    *,
    filename: str = "document.pdf",
    progress: ProgressCb | None = None,
) -> ConvertResult:
    """Convert PDF bytes (e.g. an HTTP upload) to Markdown.

    Writes a temporary file because pdf2image requires a path for rasterization.
    """
    if not data:
        raise ConversionError("Empty PDF payload.")
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf" if filename else "document.pdf"

    options = options or ConvertOptions()

    with tempfile.TemporaryDirectory(prefix="pdf_to_md_") as tmp:
        tmp_path = Path(tmp) / Path(filename).name
        tmp_path.write_bytes(data)

        opts = ConvertOptions(
            lang=options.lang,
            ocr_dpi=options.ocr_dpi,
            force_ocr=options.force_ocr,
            min_chars=options.min_chars,
            extract_images=options.extract_images,
            tesseract_cmd=options.tesseract_cmd,
            image_output_dir=options.image_output_dir,
            title=options.title or Path(filename).stem,
            strict_ocr=options.strict_ocr,
            page_warn_threshold=options.page_warn_threshold,
        )
        result = convert_file(tmp_path, opts, progress=progress)
        result.source_name = Path(filename).name
        return result
