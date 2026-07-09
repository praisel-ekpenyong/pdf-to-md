# PDF to Markdown

Turn a PDF into a Markdown file you can copy, edit, or save.

This app runs **on your computer**. Your files stay local unless you change how the server is set up.

## What it does

1. You upload a PDF in the browser.
2. The app reads the text from the file.
3. For scanned or photo pages (where text is not selectable), it can use OCR (optical character recognition) if those tools are installed.
4. You get Markdown output — ready to **Copy** or **Download**.

**Text PDFs** (where you can already select text) usually work right away.  
**Scanned PDFs** (like a photo of a page) need an extra one-time setup, explained below.

---

## Easiest way to run it (recommended)

This path uses **Docker Desktop**, which installs the tools needed for scanned PDFs for you.

### Before you start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and open it so it is running.
2. Put this project folder on your computer (for example on the Desktop).

### Start the app

Open **PowerShell** and run:

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
docker compose up --build
```

Wait until Docker finishes building and starting. Leave that window open while you use the app.

### Open the app

In your browser, go to:

**http://127.0.0.1:8000/**

### Use it

1. Drop a PDF into the upload area (or click to browse).
2. Click **Convert**.
3. When it finishes, use **Copy** or **Download**.

### Stop the app

In the PowerShell window, press `Ctrl + C`.

---

## Run without Docker (Windows)

Use this if you prefer Python and do not need scanned-PDF support right away.

### 1. Install Python

Install [Python 3](https://www.python.org/downloads/) if you do not already have it. During setup, choose the option to add Python to PATH.

### 2. Install and start

Open **PowerShell** in the project folder:

```powershell
cd $env:USERPROFILE\Desktop\pdf-to-md
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000/** in your browser.

### Scanned PDFs without Docker

Text PDFs work with the steps above. For scans and photo PDFs, install both of these and add them to your system PATH:

1. [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)

Or use the Docker method instead — it is simpler for most people.

---

## Status indicator

In the top-right of the page:

| Message | Meaning |
|--------|---------|
| **Ready** | Everything needed is available, including support for scans |
| **Ready · text PDFs** | Normal text PDFs work; scans need OCR setup |
| **Offline** | The app is not running — start it and refresh the page |

---

## Tips

- Keep the terminal (or Docker) window open while you use the app.
- Very large or heavily scanned documents can take a few minutes.
- If conversion looks empty, the PDF may be a scan and OCR may not be set up yet.

---

## For developers (optional)

You can also use this project as a Python library, command-line tool, or HTTP API.

**Library**

```python
from pdf_to_md import convert_bytes, ConvertOptions

result = convert_bytes(pdf_bytes, ConvertOptions(lang="eng"), filename="scan.pdf")
print(result.markdown)
```

**Command line**

```powershell
python -m pdf_to_md input.pdf
```

**API docs** (when the app is running): http://127.0.0.1:8000/docs  

**Health check:** http://127.0.0.1:8000/health  

**Upload size limit:** set `PDF_TO_MD_MAX_UPLOAD_MB` (default 25 MB locally, 50 MB in Docker).

**Tests**

```powershell
pip install pytest
pytest
```

---

## License

You may use this for personal and commercial projects.
