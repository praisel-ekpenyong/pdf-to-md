# PDF to Markdown

Convert PDF documents to Markdown using hybrid extraction: digital text first, with OCR applied only when a page lacks sufficient extractable content.

Includes a Python package, FastAPI service with asynchronous jobs, local web UI, and Docker image with Tesseract and Poppler.

## Quick start (Docker — recommended for OCR)

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
docker compose up --build
```

Open **http://127.0.0.1:8000/**  
API documentation: http://127.0.0.1:8000/docs  

## Local setup (Windows)

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### OCR system dependencies (without Docker)

1. **Tesseract OCR** — https://github.com/UB-Mannheim/tesseract/wiki  
2. **Poppler** — https://github.com/oschwartz10612/poppler-windows/releases (add `bin` to `PATH`)

Verify readiness: `GET http://127.0.0.1:8000/health`

### Tests

```powershell
pip install pytest
pytest
```

## Layout

```
pdf-to-md/
  pdf_to_md/     # Conversion library
  app/           # FastAPI + job queue
  static/        # Web UI
```

## Library

```python
from pdf_to_md import convert_bytes, ConvertOptions, probe_dependencies

result = convert_bytes(pdf_bytes, ConvertOptions(lang="eng"), filename="scan.pdf")
print(result.markdown, result.warnings, result.ocr_pages)
```

| Option | Default | Description |
|--------|---------|-------------|
| `lang` | `"eng"` | Tesseract language code(s) |
| `ocr_dpi` | `300` | Rasterization DPI for OCR |
| `force_ocr` | `False` | Run OCR on every page |
| `min_chars` | `20` | Skip OCR when a page has at least this many characters |
| `strict_ocr` | `False` | Raise if OCR is required but unavailable |

## CLI

```powershell
python -m pdf_to_md input.pdf
python -m pdf_to_md scanned.pdf --force-ocr --lang eng
```

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Dependency status |
| `POST` | `/convert` | Synchronous conversion → JSON |
| `POST` | `/convert/download` | Synchronous conversion → Markdown file |
| `POST` | `/jobs` | Start async conversion (202) |
| `GET` | `/jobs/{id}` | Job status and result |
| `GET` | `/jobs/{id}/download` | Download completed Markdown |

`PDF_TO_MD_MAX_UPLOAD_MB` defaults to `25` locally and `50` in Docker.

Jobs use an in-memory worker pool. Run a single uvicorn worker (Docker default). For multi-process scale-out, replace `app/jobs.py` with an external queue.

## License

Available for personal and commercial use.
