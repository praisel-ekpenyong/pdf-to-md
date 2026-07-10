"""In-memory background job queue for long-running PDF conversions.

Swap the JobStore implementation later (Redis, DB) without changing routes.
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pdf_to_md import ConvertOptions, ConversionError, MissingDependencyError, convert_bytes


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.queued
    progress: float = 0.0  # 0–100
    message: str = "Queued"
    source_name: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None
    # Result fields (when completed)
    markdown: str | None = None
    page_count: int | None = None
    ocr_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_public_dict(self, *, include_markdown: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "job_id": self.id,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "message": self.message,
            "source_name": self.source_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "page_count": self.page_count,
            "ocr_pages": self.ocr_pages,
            "warnings": self.warnings,
        }
        if include_markdown and self.status == JobStatus.completed:
            data["markdown"] = self.markdown
        elif include_markdown:
            data["markdown"] = None
        return data


class JobQueueFullError(RuntimeError):
    """Raised when the in-memory job store cannot accept more work."""


class JobStore:
    """Thread-safe in-memory jobs with a small worker pool."""

    def __init__(self, max_workers: int = 2, max_jobs: int = 200) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-job")
        self._max_jobs = max_jobs

    def create(
        self,
        data: bytes,
        filename: str,
        options: ConvertOptions,
    ) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(id=job_id, source_name=filename, message="Queued")
        with self._lock:
            self._prune_unlocked()
            if len(self._jobs) >= self._max_jobs:
                raise JobQueueFullError(
                    f"Job queue is full ({self._max_jobs} jobs). "
                    "Wait for existing conversions to finish, then try again."
                )
            self._jobs[job_id] = job

        self._executor.submit(self._run, job_id, data, filename, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _prune_unlocked(self) -> None:
        if len(self._jobs) < self._max_jobs:
            return
        # Drop oldest finished jobs first, then oldest queued (never running).
        overflow = len(self._jobs) - self._max_jobs + 1
        finished = sorted(
            (
                j
                for j in self._jobs.values()
                if j.status in (JobStatus.completed, JobStatus.failed)
            ),
            key=lambda j: j.updated_at,
        )
        removed = 0
        for j in finished:
            if removed >= overflow:
                break
            self._jobs.pop(j.id, None)
            removed += 1
        if removed >= overflow:
            return
        still_need = overflow - removed
        queued = sorted(
            (j for j in self._jobs.values() if j.status == JobStatus.queued),
            key=lambda j: j.created_at,
        )
        for j in queued[:still_need]:
            self._jobs.pop(j.id, None)

    def _update(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.touch()

    def _run(
        self,
        job_id: str,
        data: bytes,
        filename: str,
        options: ConvertOptions,
    ) -> None:
        self._update(
            job_id,
            status=JobStatus.running,
            progress=1.0,
            message="Starting conversion...",
        )

        def on_progress(current: int, total: int, message: str) -> None:
            total = max(total, 1)
            # Reserve 0–5% for startup, 5–98% for work
            pct = 5.0 + (current / total) * 93.0
            self._update(job_id, progress=min(pct, 98.0), message=message)

        try:
            result = convert_bytes(
                data,
                options,
                filename=filename,
                progress=on_progress,
            )
            self._update(
                job_id,
                status=JobStatus.completed,
                progress=100.0,
                message="Completed",
                markdown=result.markdown,
                page_count=result.page_count,
                ocr_pages=result.ocr_pages,
                warnings=result.warnings,
                source_name=result.source_name,
                error=None,
            )
        except (MissingDependencyError, ConversionError) as exc:
            self._update(
                job_id,
                status=JobStatus.failed,
                progress=100.0,
                message="Failed",
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover
            self._update(
                job_id,
                status=JobStatus.failed,
                progress=100.0,
                message="Failed",
                error=f"Conversion failed: {exc}",
            )


# Process-wide store (fine for single-worker uvicorn; use external queue for multi-process)
job_store = JobStore()
