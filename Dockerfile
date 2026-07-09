# PDF → Markdown API + UI with Tesseract OCR and Poppler
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDF_TO_MD_MAX_UPLOAD_MB=50

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pdf_to_md ./pdf_to_md
COPY app ./app
COPY static ./static
COPY pyproject.toml README.md ./

EXPOSE 8000

# Single worker so in-memory jobs stay consistent; scale via external queue later
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
