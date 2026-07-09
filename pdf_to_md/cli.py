"""Command-line interface: python -m pdf_to_md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_to_md.converter import ConvertOptions, convert_file
from pdf_to_md.exceptions import PdfToMdError


def _resolve_outputs(inputs: list[Path], output: str | None) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    if output:
        out = Path(output)
        if len(inputs) == 1 and out.suffix.lower() == ".md":
            pairs.append((inputs[0], out))
        else:
            out.mkdir(parents=True, exist_ok=True)
            for src in inputs:
                pairs.append((src, out / f"{src.stem}.md"))
    else:
        for src in inputs:
            pairs.append((src, src.with_suffix(".md")))
    return pairs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Convert PDF files to Markdown (hybrid digital text + OCR)."
    )
    ap.add_argument("inputs", nargs="+", help="One or more PDF files.")
    ap.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output .md file (single input) or output directory.",
    )
    ap.add_argument("--lang", default="eng", help="Tesseract language(s), e.g. eng or eng+deu.")
    ap.add_argument("--ocr-dpi", type=int, default=300, help="Rasterization DPI for OCR.")
    ap.add_argument(
        "--force-ocr",
        action="store_true",
        help="OCR every page even if digital text exists.",
    )
    ap.add_argument(
        "--tesseract-cmd",
        default=None,
        help="Path to tesseract executable if not on PATH.",
    )
    ap.add_argument(
        "--images",
        action="store_true",
        help="Extract embedded images next to the markdown file.",
    )
    ap.add_argument(
        "--min-chars",
        type=int,
        default=20,
        help="Min chars per page to skip OCR (default 20).",
    )
    args = ap.parse_args(argv)

    inputs = [Path(p) for p in args.inputs]
    missing = [p for p in inputs if not p.is_file()]
    if missing:
        for p in missing:
            print(f"error: file not found: {p}", file=sys.stderr)
        return 2

    pairs = _resolve_outputs(inputs, args.output)
    exit_code = 0

    for pdf_path, md_out in pairs:
        try:
            opts = ConvertOptions(
                lang=args.lang,
                ocr_dpi=args.ocr_dpi,
                force_ocr=args.force_ocr,
                min_chars=args.min_chars,
                extract_images=args.images,
                tesseract_cmd=args.tesseract_cmd,
                image_output_dir=(md_out.parent / f"{md_out.stem}_images")
                if args.images
                else None,
            )
            print(f"Converting: {pdf_path}")
            result = convert_file(pdf_path, opts)
            md_out.parent.mkdir(parents=True, exist_ok=True)
            md_out.write_text(result.markdown, encoding="utf-8")
            ocr_note = (
                f", OCR pages {result.ocr_pages}" if result.ocr_pages else ", no OCR"
            )
            print(f"  wrote: {md_out}  ({result.page_count} pages{ocr_note})")
        except PdfToMdError as exc:
            print(f"  [error] {pdf_path}: {exc}", file=sys.stderr)
            exit_code = 1
        except Exception as exc:
            print(f"  [error] failed to convert {pdf_path}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
