"""commerce.txt FastAPI application."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from app.schemas import FileIngestionRequest, ProcessedResponse
from app.services import (
    EffulgentParser,
    FileIngestor,
    JCrewPlpParser,
    MarkdownCompressor,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

JCREW_COMMERCE_PATH = DATA_DIR / "commerce_jcrew.txt"
COZY_COMMERCE_PATH = DATA_DIR / "commerce_cozy_knits.txt"
COZY_SOURCE_JS = DATA_DIR / "assets" / "mockup_app_page.js"


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


def _fetch_text(url: str) -> str:
    try:
        with urllib.request.urlopen(url) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        raise ValueError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network dependent
        raise ValueError(f"Failed to fetch {url}: {exc.reason}") from exc


def _extract_cozy_chunk_url(html: str, base_url: str) -> str:
    match = re.search(r'src="(/_next/static/chunks/app/page-[^"\\]+\.js)"', html)
    if not match:
        raise ValueError("Unable to locate Next.js page chunk for Cozy Knits.")
    return urljoin(base_url, match.group(1))


def _generate_from_url(target_url: str, limit: int | None = None) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are supported.")
    domain = parsed.netloc.lower()

    if "jcrew.com" in domain:
        html = _fetch_text(target_url)
        parser = JCrewPlpParser()
        products = parser.parse_html(html, limit=limit)
        title = "J.Crew catalog"
    elif "mockup-merchant.vercel.app" in domain or "effulgent-kataifi" in domain:
        base = f"{parsed.scheme}://{parsed.netloc}"
        html = _fetch_text(target_url)
        chunk_url = _extract_cozy_chunk_url(html, base)
        js_payload = _fetch_text(chunk_url)
        parser = EffulgentParser()
        products = parser.parse_js_text(js_payload, limit=limit)
        title = "Cozy Knits Co. catalog"
    else:
        raise ValueError("Unsupported site. Currently only jcrew.com and mockup-merchant.vercel.app are handled.")

    return _compressor.build_listing(products, title=title)


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


def _render_url_form() -> str:
    return """
    <html>
      <head>
        <title>commerce.txt generator</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; }
            label { display: block; margin: 0.5rem 0 0.25rem; }
            input { width: 100%; padding: 0.5rem; }
        </style>
      </head>
      <body>
        <h1>commerce.txt generator</h1>
        <form method="get">
            <label for="url">Product listing URL</label>
            <input type="url" id="url" name="url" placeholder="https://www.jcrew.com/..." required />
            <label for="limit">Item limit (optional)</label>
            <input type="number" id="limit" name="limit" min="1" />
            <button type="submit">Generate</button>
        </form>
        <p>Currently supports listings from jcrew.com and mockup-merchant.vercel.app. The output streams back as plain text.</p>
      </body>
    </html>
    """


@app.get("/generate", include_in_schema=False)
def generate_from_url(url: str | None = None, limit: int | None = None):
    if not url:
        return HTMLResponse(_render_url_form())

    try:
        markdown = _generate_from_url(url, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )
