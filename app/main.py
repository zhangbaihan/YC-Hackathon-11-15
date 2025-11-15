"""commerce.txt FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from app.schemas import FileIngestionRequest, ProcessedResponse
from app.services import FileIngestor, MarkdownCompressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

JCREW_COMMERCE_PATH = DATA_DIR / "commerce_jcrew.txt"
COZY_COMMERCE_PATH = DATA_DIR / "commerce_cozy_knits.txt"

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


def _read_markdown(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _ensure_jcrew_markdown() -> str:
    return _read_markdown(JCREW_COMMERCE_PATH)


def _ensure_cozy_markdown() -> str:
    return _read_markdown(COZY_COMMERCE_PATH)


@app.on_event("startup")
def initialize_commerce_txt() -> None:  # pragma: no cover - integration side effect
    for path in (JCREW_COMMERCE_PATH, COZY_COMMERCE_PATH):
        if not path.exists():
            print(f"commerce artifact missing: {path}")


def _serve_markdown(builder) -> PlainTextResponse:
    try:
        markdown = builder()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.get(
    "/jcrew/commerce.txt",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
def serve_jcrew_txt() -> PlainTextResponse:
    return _serve_markdown(_ensure_jcrew_markdown)


@app.get(
    "/cozyknits/commerce.txt",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
def serve_cozy_knits_txt() -> PlainTextResponse:
    return _serve_markdown(_ensure_cozy_markdown)


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
