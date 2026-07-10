"""Pydantic models for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    digital_extract_available: bool
    ocr_python_packages: bool
    tesseract_available: bool
    tesseract_version: str | None = None
    poppler_available: bool
    ocr_ready: bool
    messages: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    max_upload_mb: int = 25


class ConvertResponse(BaseModel):
    markdown: str
    page_count: int
    ocr_pages: list[int] = Field(default_factory=list)
    source_name: str = ""
    warnings: list[str] = Field(default_factory=list)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str = "Queued"


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: float
    message: str
    source_name: str = ""
    created_at: float | None = None
    updated_at: float | None = None
    error: str | None = None
    page_count: int | None = None
    ocr_pages: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    markdown: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobStatusResponse:
        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})
