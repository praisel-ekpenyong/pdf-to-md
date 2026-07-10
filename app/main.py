"""FastAPI application factory.

Run:
  cd Desktop/pdf-to-md
  pip install -r requirements.txt
  uvicorn app.main:app --reload
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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
        # Register HTML pages BEFORE the static mount so paths never get swallowed.
        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(_STATIC / "index.html")

        @app.get("/output", include_in_schema=False)
        @app.get("/output/", include_in_schema=False)
        def output_page() -> FileResponse:
            path = _STATIC / "output.html"
            if not path.is_file():
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Output page is not installed.")
            return FileResponse(path)

        app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> FileResponse | JSONResponse:
        # Browser navigations get the branded 404; API clients keep JSON.
        if exc.status_code == 404 and _STATIC.is_dir():
            accept = request.headers.get("accept", "")
            wants_html = "text/html" in accept
            page = _STATIC / "404.html"
            if wants_html and page.is_file():
                return FileResponse(page, status_code=404)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    return app


app = create_app()
