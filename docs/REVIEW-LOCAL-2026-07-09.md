# Local-only review — pdf-to-md

**Date:** 2026-07-09  
**Scope:** Personal use on `127.0.0.1` (venv or Docker). No public deploy.  
**Verdict:** Fit for purpose as a local tool. Architecture is good. Main gap is **OCR system deps on bare Windows**, not app design.

---

## Summary

For local-only use the project is in good shape: UI + jobs + library + Docker path cover the intended workflow. Digital PDFs work today without extra install. Scanned PDFs need Docker or Tesseract+Poppler on PATH. Most “production” review items (auth, Redis, multi-instance, public CORS) are **out of scope** and should not be prioritized.

---

## Current machine status

| Check | Status |
|--------|--------|
| Python packages (pdfplumber, pypdf, OCR libs) | OK |
| Digital text extraction | OK |
| Tesseract on PATH | Missing |
| Poppler (`pdftoppm`) on PATH | Missing |
| `ocr_ready` | **false** |
| API routes | Present (`/`, `/health`, `/jobs`, `/convert`, …) |

**Implication:** Local venv mode = digital PDFs fine, scans weak until OCR installed or Docker used.

---

## What works well (local)

- Same-origin UI at `/` talking to `/jobs` (no CORS pain in normal use)
- Background jobs + progress bar (right for slow OCR)
- Health banner when OCR incomplete
- Hybrid extract: digital first, OCR only sparse pages
- CLI + library for scripts without the browser
- Docker Compose for “full OCR without fighting Windows PATH”
- Upload size cap (default 25 MB) still useful so you don’t accidentally load a monster file
- In-memory jobs OK for single `uvicorn` process on one machine

---

## Must-do for local? 

**Almost none in the codebase.** The app is usable as-is for digital PDFs.

| Item | Must? | Notes |
|------|--------|--------|
| Install Tesseract + Poppler **or** use Docker | **Only if you need scanned/image PDFs** | Environment, not code |
| Run on `127.0.0.1` (not `0.0.0.0` unless you mean to) | Recommended | README already uses 127.0.0.1 for venv |
| Wire Poppler path into `pdf2image` | **Nice must-if** you install Poppler off-PATH | Bug only in that install style |
| Auth, Redis, rate limits, public hardening | **No** | Local-only |
| Netlify/Vercel deploy prep | **No** | Explicitly deferred |

**If there is a “must” at all for full local feature parity:** get OCR working once (Docker preferred on Windows), then treat the rest as optional polish.

---

## Will add bugs / can break things (local)

Do **not** rush these “for production” ideas into a local tool:

| Change | Risk locally |
|--------|----------------|
| Strict OCR failures by default | “Broken” on partial digital PDFs that soft-warn today |
| Aggressive page/DPI caps | Rejects PDFs you want to convert at home |
| Redis / multi-worker jobs | Overkill; half-migration → lost jobs under `--reload` |
| Auth on every request | Friction; easy to lock yourself out of the UI |
| Non-root Docker without testing volumes | Permission errors writing temps |
| Serverless-style timeout hacks | Irrelevant locally; can confuse the job model |

**Safe local polish (low break risk):**

- Pass discovered `poppler_path` into `convert_from_path`
- Single `probe_dependencies()` call per convert
- Image magic-byte sniffing
- `.gitignore` if you put it in git
- Small pytest suite with a digital PDF fixture

---

## Not applicable / not worth it (local)

| Old concern | Local verdict |
|-------------|----------------|
| Public auth / API keys | N/A |
| Multi-instance job store | N/A (one process) |
| CORS lockdown for Netlify domain | N/A (same origin) |
| Docker bind only for “public internet” | N/A; still prefer 127.0.0.1 for host port |
| Cloud free tiers | N/A |
| Desktop `.exe` rewrite | Optional later, not needed |

CORS `*` + credentials is still *incorrect* in theory but **does not hurt** same-origin local UI. Fix later only if you open the API to another local origin (e.g. Vite on :5173).

---

## Local issues still real (severity for *local*)

### 1. OCR stack not installed (user env) — **blocks scans**
- Severity (local): **high if you need OCR**, else low  
- Fix: `docker compose up --build` **or** install Tesseract + Poppler and add to PATH  

### 2. Poppler path discovery not used by pdf2image — **bug**
- Severity (local): medium (only if Poppler installed but not on PATH)  
- File: `deps.py` / `ocr.py`  

### 3. No page limit — **can freeze your PC**
- Severity (local): medium (self-DoS on a 500-page scan at 400 DPI)  
- Optional: soft warning in UI or cap with override  

### 4. Image extract always `.png` — **quality**
- Severity (local): low  
- CLI/`--images` path; UI doesn’t extract images  

### 5. Markdown is page-plain-text — **quality**
- Severity (local): low / expected for v1  

### 6. No automated tests — **maintenance**
- Severity (local): low until you change core often  

### 7. Jobs lost on server restart / `--reload`  
- Severity (local): low; expected for in-memory  

---

## How to use it well locally

**Digital PDFs (current Windows venv):**
```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
→ http://127.0.0.1:8000/

**Scanned PDFs (recommended):**
```powershell
docker compose up --build
```

**CLI:**
```powershell
python -m pdf_to_md some.pdf
```

Check OCR readiness anytime: http://127.0.0.1:8000/health

---

## Local scorecard

| Dimension | Score (1–5) | Comment |
|-----------|-------------|---------|
| Architecture for local tool | 5 | Right split library/API/UI |
| Digital PDF conversion | 4–5 | Solid |
| Scanned PDF (this machine, no Docker) | 1–2 | Missing Tesseract/Poppler |
| Scanned PDF (with Docker) | 4 | Designed path |
| UX (upload, jobs, progress) | 4 | Good enough |
| Safety on your machine | 3–4 | Watch huge scans / RAM |
| Deploy readiness | N/A | Intentionally local |

**Overall (local digital use): ready.**  
**Overall (local full OCR): ready after Docker or system OCR install.**

---

## Recommended local priority (only if you keep improving)

1. Use Docker when you need OCR (no code change)  
2. Optional code: wire `poppler_path` so non-PATH Windows installs work  
3. Optional: soft max-pages warning in UI  
4. Skip auth/Redis/cloud until requirements change  

---

## Bottom line

For **local as-is**, the earlier “production” review overstated urgency.  

- **Must in code:** none for digital PDFs.  
- **Must for OCR:** environment (Docker or Tesseract+Poppler), not a rewrite.  
- **Don’t do:** production hardening that adds friction or breakage.  
- **Ship/use:** yes for localhost; prefer Docker when converting scans.
