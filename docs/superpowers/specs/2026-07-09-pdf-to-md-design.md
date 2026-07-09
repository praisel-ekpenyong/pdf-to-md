# PDF → Markdown Converter (Webapp Foundation)

**Date:** 2026-07-09  
**Status:** Approved  
**Location:** `Desktop/pdf-to-md/`

## Goal

Provide a reusable Python package and thin FastAPI skeleton so a webapp can upload PDFs and receive Markdown. Hybrid extraction: digital text first; OCR only when a page has little/no extractable text.

## Architecture

```
pdf_to_md/          # importable library
  converter.py      # convert_file / convert_bytes / ConvertResult
  extract.py        # pdfplumber + pypdf
  ocr.py            # pdf2image + Tesseract
  images.py         # optional embedded images
  markdown.py       # pages → markdown
  cli.py            # python -m pdf_to_md

app/                # FastAPI thin layer
  main.py
  routes.py
  schemas.py
```

## Library API

- `convert_file(path, options?) -> ConvertResult`
- `convert_bytes(data, options?, filename?) -> ConvertResult`
- `ConvertOptions`: lang, ocr_dpi, force_ocr, min_chars, extract_images, tesseract_cmd, image_output_dir
- `ConvertResult`: markdown, page_count, ocr_pages, images, source_name

## HTTP API

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/health` | status + ocr_available |
| POST | `/convert` | multipart PDF → JSON markdown |
| POST | `/convert/download` | multipart PDF → .md file |

Guards: max upload size (default 25 MB). CORS open for local dev.

## Out of scope (v1)

Job queue, auth, ML layout reconstruction.

## Added after v1 approval

- Minimal static web UI under `static/` served at `GET /` (drag-drop upload, options, preview, copy, download).
- Dependency probe (`pdf_to_md.deps`) for Tesseract + Poppler; `/health` exposes readiness + hints.
- Background jobs: `POST /jobs`, `GET /jobs/{id}`, in-memory thread pool (`app/jobs.py`); UI polls with progress bar.
- Docker / docker-compose with Tesseract + Poppler preinstalled.

## System deps

Tesseract OCR + Poppler (Windows install links in README).
