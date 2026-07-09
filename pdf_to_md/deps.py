"""Detect optional Python packages and system binaries (Tesseract, Poppler)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyReport:
    """Snapshot of what is available for conversion / OCR."""

    digital_extract_available: bool
    ocr_python_packages: bool
    tesseract_available: bool
    poppler_available: bool
    tesseract_version: str | None = None
    tesseract_path: str | None = None
    poppler_path: str | None = None  # full path to pdftoppm if known
    ocr_ready: bool = False
    messages: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "digital_extract_available": self.digital_extract_available,
            "ocr_python_packages": self.ocr_python_packages,
            "tesseract_available": self.tesseract_available,
            "tesseract_version": self.tesseract_version,
            "tesseract_path": self.tesseract_path,
            "poppler_available": self.poppler_available,
            "poppler_path": self.poppler_path,
            "ocr_ready": self.ocr_ready,
            "messages": self.messages,
            "hints": self.hints,
        }

    @property
    def poppler_bin_dir(self) -> str | None:
        """Directory containing pdftoppm (what pdf2image expects)."""
        return poppler_bin_dir(self.poppler_path)


def path_exists(p: str) -> bool:
    return Path(p).is_file()


def poppler_bin_dir(pdftoppm_path: str | None) -> str | None:
    """Return the folder pdf2image should receive as poppler_path=.

    Accepts a path to ``pdftoppm`` / ``pdftoppm.exe`` or to the bin directory.
    Works even if the path is not present on this machine (string logic only).
    """
    if not pdftoppm_path:
        return None
    p = Path(pdftoppm_path)
    name = p.name.lower()
    if name in ("pdftoppm", "pdftoppm.exe") or p.suffix.lower() in (".exe",):
        return str(p.parent)
    if p.is_dir():
        return str(p)
    # Heuristic: path ends with bin-like folder name
    if name in ("bin", "library"):
        return str(p)
    # Existing file that isn't named pdftoppm — still use parent
    if p.is_file():
        return str(p.parent)
    return None


def _check_tesseract(
    tesseract_cmd: str | None = None,
) -> tuple[bool, str | None, str | None, str | None]:
    """Returns (ok, version, path, error)."""
    try:
        import pytesseract
    except ImportError:
        return False, None, None, "pytesseract not installed"

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", None) or "tesseract"
    path = shutil.which(str(cmd)) if not tesseract_cmd else tesseract_cmd
    if tesseract_cmd and not path_exists(tesseract_cmd):
        which = shutil.which(tesseract_cmd)
        path = which or tesseract_cmd

    try:
        version = str(pytesseract.get_tesseract_version())
        return True, version, path or str(cmd), None
    except Exception as exc:
        candidates = [
            tesseract_cmd,
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "tesseract",
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                if cand != "tesseract" and not path_exists(cand) and not shutil.which(cand):
                    continue
                if cand != "tesseract":
                    pytesseract.pytesseract.tesseract_cmd = cand
                version = str(pytesseract.get_tesseract_version())
                resolved = (
                    cand
                    if cand != "tesseract"
                    else (shutil.which("tesseract") or "tesseract")
                )
                return True, version, resolved, None
            except Exception:
                continue
        return False, None, path, str(exc)


def _check_poppler() -> tuple[bool, str | None, str | None]:
    """Returns (ok, path_to_pdftoppm, error)."""
    for name in ("pdftoppm", "pdftoppm.exe"):
        path = shutil.which(name)
        if path:
            try:
                subprocess.run(
                    [path, "-v"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return True, path, None
            except Exception as exc:
                return False, path, str(exc)

    common = [
        Path(r"C:\Program Files\poppler\Library\bin\pdftoppm.exe"),
        Path(r"C:\poppler\Library\bin\pdftoppm.exe"),
        Path(r"C:\tools\poppler\Library\bin\pdftoppm.exe"),
    ]
    for p in common:
        if p.is_file():
            return True, str(p), None

    return (
        False,
        None,
        "pdftoppm not found on PATH (install Poppler and add its bin folder to PATH)",
    )


def probe_dependencies(tesseract_cmd: str | None = None) -> DependencyReport:
    """Probe digital extractors + full OCR stack."""
    from pdf_to_md.extract import digital_stack_available
    from pdf_to_md.ocr import ocr_available as ocr_packages

    digital = digital_stack_available()
    packages = ocr_packages()
    tess_ok, tess_ver, tess_path, tess_err = (
        _check_tesseract(tesseract_cmd)
        if packages
        else (False, None, None, "OCR Python packages missing")
    )
    pop_ok, pop_path, pop_err = (
        _check_poppler() if packages else (False, None, "OCR Python packages missing")
    )

    messages: list[str] = []
    hints: list[str] = []

    if not digital:
        messages.append("Digital PDF text extractors (pdfplumber/pypdf) are not available.")
        hints.append("pip install pdfplumber pypdf")

    if not packages:
        messages.append("OCR Python packages (pytesseract/pdf2image) are not installed.")
        hints.append("pip install pytesseract pdf2image pillow")
    else:
        if not tess_ok:
            messages.append(f"Tesseract OCR engine not usable: {tess_err or 'not found'}")
            hints.append(
                "Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki "
                "and ensure tesseract.exe is on PATH (or set tesseract_cmd)."
            )
        if not pop_ok:
            messages.append(f"Poppler not usable: {pop_err or 'not found'}")
            hints.append(
                "Install Poppler for Windows: "
                "https://github.com/oschwartz10612/poppler-windows/releases "
                "and add the bin folder to PATH — or use docker compose."
            )

    ready = bool(packages and tess_ok and pop_ok)
    if ready:
        messages.append("OCR stack is ready (packages + Tesseract + Poppler).")
    elif digital:
        messages.append("Digital PDFs can convert; scanned pages need a working OCR stack.")

    return DependencyReport(
        digital_extract_available=digital,
        ocr_python_packages=packages,
        tesseract_available=tess_ok,
        tesseract_version=tess_ver,
        tesseract_path=tess_path,
        poppler_available=pop_ok,
        poppler_path=pop_path,
        ocr_ready=ready,
        messages=messages,
        hints=hints,
    )


def format_dependency_issues(report: DependencyReport) -> str:
    """Human-readable OCR setup issues from an existing report (no re-probe)."""
    if report.ocr_ready:
        return ""
    parts = list(report.messages)
    if report.hints:
        parts.append("Hints:")
        parts.extend(report.hints)
    return "\n".join(parts)


def ocr_ready(tesseract_cmd: str | None = None) -> bool:
    return probe_dependencies(tesseract_cmd).ocr_ready


def ocr_not_ready_message(tesseract_cmd: str | None = None) -> str:
    return format_dependency_issues(probe_dependencies(tesseract_cmd))
