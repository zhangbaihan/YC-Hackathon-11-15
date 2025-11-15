"""commerce.txt FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from app.schemas import FileIngestionRequest, ProcessedResponse
from app.services import (
    CommercePipeline,
    FileIngestor,
    JCrewPlpParser,
    MarkdownCompressor,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JCREW_SOURCE_HTML = DATA_DIR / "jcrew_mens_sweaters.html"
COMMERCE_TXT_PATH = DATA_DIR / "commerce.txt"
COMMERCE_TITLE = "J.Crew men sweaters"

app = FastAPI(
    title="commerce.txt",
    description=(
        "Ingest product data from files (scraping coming soon) and compress it into"
        " context-optimized markdown for AI agents."
    ),
    version="0.1.0",
)

_ingestor = FileIngestor(base_dir=PROJECT_ROOT)
_compressor = MarkdownCompressor()
_pipeline = CommercePipeline(parser=JCrewPlpParser(), compressor=_compressor)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process/from-file", response_model=ProcessedResponse)
def process_from_file(payload: FileIngestionRequest) -> ProcessedResponse:
    try:
        products = _ingestor.load_products(payload.path, limit=payload.max_items)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"File not found: {exc}") from exc
    except ValueError as exc:  # Failed validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    markdown = _compressor.build_listing(products, title=payload.title)
    return ProcessedResponse(markdown=markdown, items=products)


def _ensure_commerce_markdown() -> str:
    try:
        return _build_commerce_markdown()
    except FileNotFoundError:
        if COMMERCE_TXT_PATH.exists():
            return COMMERCE_TXT_PATH.read_text(encoding="utf-8")
        raise


def _build_commerce_markdown() -> str:
    if not JCREW_SOURCE_HTML.exists():
        raise FileNotFoundError(JCREW_SOURCE_HTML)
    return _pipeline.write_markdown(
        JCREW_SOURCE_HTML, COMMERCE_TXT_PATH, title=COMMERCE_TITLE
    )


@app.on_event("startup")
def initialize_commerce_txt() -> None:  # pragma: no cover - integration side effect
    try:
        _ensure_commerce_markdown()
    except Exception as exc:
        # Surface startup issues in logs without failing healthcheck.
        print(f"commerce.txt generation skipped: {exc}")


@app.get(
    "/commerce.txt",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
def serve_commerce_txt() -> PlainTextResponse:
    try:
        markdown = _ensure_commerce_markdown()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/robots.txt", include_in_schema=False)
def robots_txt() -> FileResponse:
    robots_path = PROJECT_ROOT / "robots.txt"
    if not robots_path.exists():
        raise HTTPException(status_code=404, detail="robots.txt not found")
    return FileResponse(
        robots_path,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )
