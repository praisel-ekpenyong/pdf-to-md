"""HTTP routes for conversion and background jobs."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.jobs import JobQueueFullError, job_store
from app.schemas import (
    ConvertResponse,
    HealthResponse,
    JobCreateResponse,
    JobStatusResponse,
)
from pdf_to_md import (
    ConvertOptions,
    ConversionError,
    MissingDependencyError,
    convert_bytes,
    __version__,
)
from pdf_to_md.deps import probe_dependencies

router = APIRouter()

DEFAULT_MAX_UPLOAD_MB = 25


def _max_upload_mb() -> int:
    try:
        mb = int(os.environ.get("PDF_TO_MD_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
    except ValueError:
        mb = DEFAULT_MAX_UPLOAD_MB
    return max(1, mb)


def _max_upload_bytes() -> int:
    return _max_upload_mb() * 1024 * 1024


def _safe_download_stem(name: str) -> str:
    """ASCII-safe filename stem for Content-Disposition filename=."""
    stem = Path(name or "document").stem
    safe = re.sub(r"[^\w.\-]+", "_", stem, flags=re.UNICODE).strip("._")
    return (safe[:80] or "document")


def _content_disposition(md_filename: str) -> str:
    """Build a safe Content-Disposition with ASCII fallback + RFC 5987 UTF-8."""
    stem = Path(md_filename).stem if md_filename else "document"
    ascii_stem = _safe_download_stem(stem)
    ascii_name = f"{ascii_stem}.md"
    # Prefer original stem for UTF-8 filename* when it differs.
    raw_name = f"{(stem or 'document')[:120]}.md"
    utf8_name = quote(raw_name, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    report = probe_dependencies()
    return HealthResponse(
        status="ok" if report.digital_extract_available or report.ocr_ready else "degraded",
        version=__version__,
        digital_extract_available=report.digital_extract_available,
        ocr_python_packages=report.ocr_python_packages,
        tesseract_available=report.tesseract_available,
        tesseract_version=report.tesseract_version,
        poppler_available=report.poppler_available,
        ocr_ready=report.ocr_ready,
        messages=report.messages,
        hints=report.hints,
        max_upload_mb=_max_upload_mb(),
    )


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    name = Path(file.filename).name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    data = await file.read()
    max_bytes = _max_upload_bytes()
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size ({max_bytes // (1024 * 1024)} MB).",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    return data, name


def _options_from_form(
    lang: str,
    force_ocr: bool,
    ocr_dpi: int,
    min_chars: int,
) -> ConvertOptions:
    return ConvertOptions(
        lang=lang,
        force_ocr=force_ocr,
        ocr_dpi=ocr_dpi,
        min_chars=min_chars,
        extract_images=False,
    )


@router.post("/convert", response_model=ConvertResponse)
async def convert(
    file: UploadFile = File(..., description="PDF file to convert"),
    lang: str = Form("eng"),
    force_ocr: bool = Form(False),
    ocr_dpi: int = Form(300),
    min_chars: int = Form(20),
) -> ConvertResponse:
    """Synchronous convert (fine for small digital PDFs). Prefer /jobs for OCR."""
    data, name = await _read_upload(file)
    opts = _options_from_form(lang, force_ocr, ocr_dpi, min_chars)
    try:
        result = convert_bytes(data, opts, filename=name)
    except MissingDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc

    return ConvertResponse(
        markdown=result.markdown,
        page_count=result.page_count,
        ocr_pages=result.ocr_pages,
        source_name=result.source_name,
        warnings=result.warnings,
    )


@router.post("/convert/download")
async def convert_download(
    file: UploadFile = File(..., description="PDF file to convert"),
    lang: str = Form("eng"),
    force_ocr: bool = Form(False),
    ocr_dpi: int = Form(300),
    min_chars: int = Form(20),
) -> PlainTextResponse:
    """Synchronous convert → download .md file."""
    data, name = await _read_upload(file)
    opts = _options_from_form(lang, force_ocr, ocr_dpi, min_chars)
    try:
        result = convert_bytes(data, opts, filename=name)
    except MissingDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc

    md_name = f"{Path(name).stem}.md"
    return PlainTextResponse(
        content=result.markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(md_name)},
    )


@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(
    file: UploadFile = File(..., description="PDF file to convert asynchronously"),
    lang: str = Form("eng"),
    force_ocr: bool = Form(False),
    ocr_dpi: int = Form(300),
    min_chars: int = Form(20),
) -> JobCreateResponse:
    """Enqueue conversion. Poll GET /jobs/{job_id} for progress and result."""
    data, name = await _read_upload(file)
    opts = _options_from_form(lang, force_ocr, ocr_dpi, min_chars)
    try:
        job = job_store.create(data, name, opts)
    except JobQueueFullError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return JobCreateResponse(job_id=job.id, status=job.status.value, message=job.message)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse.from_dict(job.to_public_dict(include_markdown=True))


@router.get("/jobs/{job_id}/download")
def download_job_markdown(job_id: str) -> PlainTextResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status.value != "completed" or job.markdown is None:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not ready for download (status={job.status.value}).",
        )
    stem = Path(job.source_name or "document").stem
    return PlainTextResponse(
        content=job.markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(f"{stem}.md")},
    )
