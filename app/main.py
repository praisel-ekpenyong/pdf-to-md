"""FastAPI application factory.

Run:
  cd Desktop/pdf-to-md
  pip install -r requirements.txt
  uvicorn app.main:app --reload
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure project root is on sys.path when launched via uvicorn from elsewhere
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.routes import router  # noqa: E402
from pdf_to_md import __version__  # noqa: E402

_STATIC = _ROOT / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="PDF to Markdown",
        description=(
            "Convert PDF documents to Markdown using hybrid digital extraction "
            "with OCR fallback. Includes library API, asynchronous jobs, and a local web UI."
        ),
        version=__version__,
    )
    # Same-origin UI needs no credentials; avoid invalid "*" + credentials combo.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    if _STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(_STATIC / "index.html")

    return app


app = create_app()
