# PDF to Markdown

A local tool that converts PDF files into Markdown text you can copy, edit, and save.

The application runs on your computer. Files are processed locally and are not uploaded to an external service.

---

## Overview

| Topic | Summary |
|--------|---------|
| **Purpose** | Convert a PDF into Markdown |
| **How you use it** | Open a page in your browser, select a file, convert |
| **Privacy** | Processing stays on your machine |
| **Best for** | Notes, documentation, and reusable text from PDFs |

### How conversion works

1. You select a PDF in the browser.
2. The app extracts existing text from the document.
3. If a page is a scan or image (no selectable text), it can read that page with OCR when the required tools are available. OCR means software that recognizes text in images.
4. The result is Markdown, which you can copy or download as a `.md` file.

**Text-based PDFs** (you can already select text with the mouse) usually convert immediately.  
**Scanned PDFs** (photographs or image-only pages) need a one-time setup so the app can read those pages. The recommended setup below includes that support automatically.

---

## Requirements

Choose one of the two setup options below.

| Option | Best if you… | Supports scanned PDFs |
|--------|----------------|------------------------|
| **A — Docker** (recommended) | Want the simplest full setup on your machine | Yes (included) |
| **B — Python only** | Prefer not to use Docker | Text PDFs only, unless you install extra tools |
| **C — Render (free)** | Want a public URL with no local server | Yes (included in Docker image) |

You will also need a modern web browser (Chrome, Edge, Firefox, or Safari).

---

## Option A — Run with Docker (recommended)

Docker Desktop packages the application and the tools needed for scanned documents so you do not install them separately.

### 1. Prepare

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. Place this project folder on your computer (for example: `Desktop\pdf-to-md`).

### 2. Start the application

Open PowerShell, then run:

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
docker compose up --build
```

Wait until startup finishes. Leave this window open while you use the app.

### 3. Open the interface

In your browser, go to:

**http://127.0.0.1:8000/**

### 4. Convert a file

1. Drop a PDF onto the upload area, or click to browse.
2. Select **Convert**.
3. When conversion finishes, use **Copy** or **Download**.

### 5. Stop the application

In the PowerShell window, press **Ctrl+C**.

---

## Option B — Run with Python (Windows)

Use this option if you already use Python and mainly convert text-based PDFs.

### 1. Install Python

Install [Python 3](https://www.python.org/downloads/). During installation, enable **Add Python to PATH**.

### 2. Install and start

Open PowerShell in the project folder:

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** in your browser and convert files as described above.

### Support for scanned PDFs (optional)

Without Docker, scanned pages require two additional programs on your computer, both added to the system PATH:

1. [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)

If that setup is unfamiliar, use **Option A (Docker)** instead.

---

## Understanding the status indicator

The label in the top-right of the page shows whether the service is ready:

| Status | Meaning |
|--------|---------|
| **Ready** | Conversion is available, including support for scanned pages |
| **Ready · text PDFs** | Text-based PDFs work; scanned pages need OCR setup |
| **Offline** | The application is not running. Start it, then refresh the page |

---

## Practical notes

- Keep the PowerShell or Docker window open for as long as you use the app.
- Large files or multi-page scans may take several minutes.
- If the result is empty, the PDF may be image-based and OCR may not be configured yet.
- The address `127.0.0.1` means “this computer only.” Other people on the internet cannot reach your app through that link under the default setup.

---

## Option C — Deploy free on Render

Host the full app (API + UI + OCR) on [Render](https://render.com)’s free web service tier. This uses the project `Dockerfile` and `render.yaml`.

### What you get

| | |
|--|--|
| **Cost** | Free instance type (`plan: free`) |
| **URL** | Public `https://….onrender.com` with HTTPS |
| **OCR** | Included (Tesseract + Poppler in the image) |

### Limits (free tier)

- The service **sleeps after ~15 minutes** of no traffic. The first request after sleep can take about a minute.
- Free instance hours are limited per month (see [Render free docs](https://render.com/docs/free)).
- Large or heavily scanned PDFs may be slow or fail on small free resources.
- Files are processed on Render’s servers, **not** only on your machine. Do not upload confidential documents unless you accept that.

### Deploy steps

1. Push this repository to **GitHub** (or GitLab / Bitbucket).
2. Sign up at [render.com](https://render.com) (no credit card required for free).
3. **New → Blueprint** → connect the repo. Render reads `render.yaml`.
4. Confirm the **Free** plan and create the service.
5. Wait for the Docker build to finish, then open the service URL.

**Manual alternative:** **New → Web Service** → connect the repo → Runtime **Docker** → instance type **Free** → set env `PDF_TO_MD_MAX_UPLOAD_MB=25` → Deploy.

After deploy, check `https://YOUR-SERVICE.onrender.com/health` — status should show ready with OCR when Tesseract/Poppler are present.

---

## For developers

Optional. Not required to use the browser interface.

**Python library**

```python
from pdf_to_md import convert_bytes, ConvertOptions

result = convert_bytes(pdf_bytes, ConvertOptions(lang="eng"), filename="document.pdf")
print(result.markdown)
```

**Command line**

```powershell
python -m pdf_to_md input.pdf
```

**Useful URLs** (while the app is running)

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Web interface |
| http://127.0.0.1:8000/docs | API documentation |
| http://127.0.0.1:8000/health | Dependency and readiness check |

**Configuration**

- Maximum upload size: environment variable `PDF_TO_MD_MAX_UPLOAD_MB` (default 25 MB without Docker, 50 MB with Docker).

**Tests**

```powershell
pip install pytest
pytest
```

---

## Author

**Praisel Ekpenyong**  
GitHub: [praisel-ekpenyong](https://github.com/praisel-ekpenyong)

Maintained as an open-source local PDF to Markdown tool.

---

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 Praisel Ekpenyong.
