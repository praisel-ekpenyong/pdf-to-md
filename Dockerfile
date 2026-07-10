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

# Render and similar hosts inject PORT; local Docker defaults to 8000
ENV PORT=8000
EXPOSE 8000

# Single worker so in-memory jobs stay consistent; scale via external queue later
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
