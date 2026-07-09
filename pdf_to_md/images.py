"""Best-effort extraction of embedded PDF images."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None


def sanitize_filename(name: str) -> str:
    keep = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return keep or "image"


def detect_image_extension(data: bytes) -> str:
    """Guess a file extension from magic bytes. Falls back to 'bin'."""
    if not data or len(data) < 4:
        return "bin"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    # PDF-inline JPEG often still starts with FF D8
    if data[:2] == b"\xff\xd8":
        return "jpg"
    return "bin"


def extract_images(
    pdf_path: Path,
    output_dir: Path,
    doc_stem: str,
) -> dict[int, list[str]]:
    """Extract embedded images keyed by 0-based page index.

    Returns map: page_index -> list of image filenames (relative basenames).
    """
    if pdfplumber is None:
        return {}

    images: dict[int, list[str]] = {}
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = sanitize_filename(doc_stem)

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages):
                for j, img in enumerate(page.images or []):
                    try:
                        stream = img.get("stream")
                        if stream is None:
                            continue
                        data = (
                            stream.get_rawdata()
                            if hasattr(stream, "get_rawdata")
                            else None
                        )
                        if not data:
                            continue
                        ext = detect_image_extension(data)
                        fname = f"{stem}_p{idx + 1}_img{j + 1}.{ext}"
                        fpath = output_dir / fname
                        fpath.write_bytes(data)
                        images.setdefault(idx, []).append(fname)
                    except Exception as exc:  # pragma: no cover
                        print(
                            f"  [warn] image extraction p{idx + 1}: {exc}",
                            file=sys.stderr,
                        )
    except Exception as exc:  # pragma: no cover
        print(f"  [warn] image scan failed: {exc}", file=sys.stderr)
    return images
