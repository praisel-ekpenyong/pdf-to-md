# pdf-to-md

Convert PDF files to Markdown with **hybrid OCR** (digital text first, Tesseract only when a page is sparse). Built as a **Python package + FastAPI app** with:

- Background **jobs** (progress-friendly for large / scanned PDFs)
- Dependency **health** checks (Tesseract + Poppler)
- Browser **upload UI**
- **Docker** image with OCR stack preinstalled

## Quick start (Docker — recommended for OCR)

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
docker compose up --build
```

Open **http://127.0.0.1:8000/**  
API docs: http://127.0.0.1:8000/docs  

Docker includes **Tesseract** + **Poppler** so scanned PDFs work out of the box.

## Local setup (Windows)

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### System dependencies (for OCR without Docker)

1. **Tesseract OCR** — https://github.com/UB-Mannheim/tesseract/wiki  
2. **Poppler** — https://github.com/oschwartz10612/poppler-windows/releases (add `bin` to PATH)

The app probes common Windows install paths and passes Poppler’s bin dir into `pdf2image` when found (PATH still recommended).

Check readiness:

```text
GET http://127.0.0.1:8000/health
```

### Tests

```powershell
pip install pytest
pytest
```

## Project layout

```
pdf-to-md/
  pdf_to_md/     # importable library
  app/           # FastAPI + in-memory job queue
  static/        # web UI
  Dockerfile
  docker-compose.yml
```

## Library usage

```python
from pdf_to_md import convert_file, convert_bytes, ConvertOptions, probe_dependencies

print(probe_dependencies().ocr_ready)

result = convert_bytes(pdf_bytes, ConvertOptions(lang="eng"), filename="scan.pdf")
print(result.markdown, result.warnings, result.ocr_pages)
```

### `ConvertOptions`

| Field | Default | Meaning |
|-------|---------|---------|
| `lang` | `"eng"` | Tesseract language(s) |
| `ocr_dpi` | `300` | Raster DPI for OCR |
| `force_ocr` | `False` | OCR every page |
| `min_chars` | `20` | Below this, page is OCRed |
| `strict_ocr` | `False` | Raise if OCR stack fails |

## CLI

```powershell
python -m pdf_to_md input.pdf
python -m pdf_to_md scanned.pdf --force-ocr --lang eng
```

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Upload UI |
| `GET` | `/health` | Digital + Tesseract + Poppler status |
| `POST` | `/convert` | Sync convert → JSON (small PDFs) |
| `POST` | `/convert/download` | Sync convert → `.md` download |
| `POST` | `/jobs` | **Async** convert → `{ job_id }` (202) |
| `GET` | `/jobs/{id}` | Job status, progress, markdown when done |
| `GET` | `/jobs/{id}/download` | Download result `.md` |

Env: `PDF_TO_MD_MAX_UPLOAD_MB` (default `25` local / `50` in Docker).

### Async job example

```powershell
# start job
curl -X POST http://127.0.0.1:8000/jobs -F "file=@doc.pdf" -F "force_ocr=false"

# poll
curl http://127.0.0.1:8000/jobs/<job_id>
```

The web UI uses `/jobs` automatically and shows a progress bar.

## Architecture notes

- **Jobs** run in a process-local thread pool (in-memory). Use **one uvicorn worker** (Docker default). For multi-process scale-out, replace `app/jobs.py` with Redis/Celery — keep `pdf_to_md` unchanged.
- **OCR** is page-by-page with progress callbacks so long scans don’t freeze the UI.
- Frontend is plain `static/` HTML/JS; swap for React/Vue later against the same API.

## Building further

1. Auth / multi-user storage in `app/`  
2. External job backend (Redis) when you need multiple workers  
3. Optional: richer frontend when product needs it  

## License

Use freely for personal and commercial projects.
