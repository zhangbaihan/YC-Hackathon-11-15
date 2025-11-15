"""commerce.txt FastAPI application."""

from __future__ import annotations

from pathlib import Path
from html import escape

from fastapi import FastAPI, HTTPException, Request
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

JCREW_SOURCE_HTML = DATA_DIR / "jcrew_mens_sweaters.html"
JCREW_COMMERCE_PATH = DATA_DIR / "commerce_jcrew.txt"
JCREW_TITLE = "J.Crew men sweaters"

COZY_SOURCE_JS = DATA_DIR / "assets" / "mockup_app_page.js"
COZY_COMMERCE_PATH = DATA_DIR / "commerce_cozy_knits.txt"
COZY_TITLE = "Cozy Knits Co. catalog"

SITE_CONFIGS = {
    "jcrew": {
        "parser": JCrewPlpParser,
        "default_source": JCREW_SOURCE_HTML,
        "default_output": JCREW_COMMERCE_PATH,
        "default_title": JCREW_TITLE,
    },
    "cozyknits": {
        "parser": EffulgentParser,
        "default_source": COZY_SOURCE_JS,
        "default_output": COZY_COMMERCE_PATH,
        "default_title": COZY_TITLE,
    },
}


def _resolve_path(path_str: str) -> Path:
    candidate = Path(path_str).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def _stringify_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)

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


def _generate_markdown(
    parser, source_path: Path, output_path: Path, title: str, limit: int | None = None
) -> str:
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    products = parser.parse_file(source_path, limit=limit)
    markdown = _compressor.build_listing(products, title=title)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def _generate_jcrew_markdown(limit: int | None = None) -> str:
    parser = JCrewPlpParser()
    return _generate_markdown(
        parser, JCREW_SOURCE_HTML, JCREW_COMMERCE_PATH, JCREW_TITLE, limit=limit
    )


def _generate_cozy_markdown(limit: int | None = None) -> str:
    parser = EffulgentParser()
    return _generate_markdown(
        parser, COZY_SOURCE_JS, COZY_COMMERCE_PATH, COZY_TITLE, limit=limit
    )


def _generate_custom_markdown(
    site_key: str,
    source: str,
    output: str,
    title: str,
    limit: int | None,
) -> str:
    config = SITE_CONFIGS.get(site_key)
    if not config:
        raise ValueError(f"Unsupported site '{site_key}'.")
    parser = config["parser"]()
    source_path = _resolve_path(source)
    output_path = _resolve_path(output)
    return _generate_markdown(parser, source_path, output_path, title, limit=limit)


def _render_generation_form(
    *,
    site: str = "jcrew",
    source: str | None = None,
    output: str | None = None,
    title: str | None = None,
    limit: str | None = None,
    message: str | None = None,
    error: str | None = None,
    markdown: str | None = None,
) -> str:
    config = SITE_CONFIGS.get(site) or SITE_CONFIGS["jcrew"]
    source = source or _stringify_path(config["default_source"])
    output = output or _stringify_path(config["default_output"])
    title = title or config["default_title"]
    limit = limit or ""
    message_html = f"<p class=\"success\">{escape(message)}</p>" if message else ""
    error_html = f"<p class=\"error\">{escape(error)}</p>" if error else ""
    markdown_html = (
        f"<h2>Generated markdown</h2><pre>{escape(markdown)}</pre>" if markdown else ""
    )
    options = []
    for key in SITE_CONFIGS:
        selected = "selected" if key == site else ""
        label = "J.Crew" if key == "jcrew" else "Cozy Knits"
        options.append(f"<option value=\"{key}\" {selected}>{label}</option>")
    options_html = "".join(options)
    return f"""
    <html>
      <head>
        <title>commerce.txt generator</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 2rem; }}
            form {{ margin-bottom: 2rem; }}
            label {{ display: block; margin: 0.5rem 0 0.25rem; }}
            input, select {{ width: 100%; padding: 0.5rem; }}
            .success {{ color: #0a6; }}
            .error {{ color: #b00; }}
            pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; }}
        </style>
      </head>
      <body>
        <h1>commerce.txt generator</h1>
        <form method=\"post\">
            <label for=\"site\">Site</label>
            <select name=\"site\" id=\"site\">{options_html}</select>

            <label for=\"source\">Source snapshot path</label>
            <input type=\"text\" id=\"source\" name=\"source\" value=\"{escape(source)}\" />

            <label for=\"output\">Output path</label>
            <input type=\"text\" id=\"output\" name=\"output\" value=\"{escape(output)}\" />

            <label for=\"title\">Markdown title</label>
            <input type=\"text\" id=\"title\" name=\"title\" value=\"{escape(title)}\" />

            <label for=\"limit\">Item limit (optional)</label>
            <input type=\"text\" id=\"limit\" name=\"limit\" value=\"{escape(limit)}\" />

            <button type=\"submit\">Generate</button>
        </form>
        {message_html}
        {error_html}
        {markdown_html}
      </body>
    </html>
    """


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


def _render_generation_page(label: str, generator) -> HTMLResponse:
    try:
        markdown = generator()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    escaped = escape(markdown)
    line_count = markdown.count("\n") + (0 if not markdown else 1)
    html_content = f"""
    <html>
        <head><title>{label} commerce.txt</title></head>
        <body>
            <h1>{label} commerce.txt</h1>
            <p>Generated {line_count} lines and wrote the artifact to disk.</p>
            <pre>{escaped}</pre>
        </body>
    </html>
    """
    return HTMLResponse(html_content)


@app.get("/jcrew/generate", response_class=HTMLResponse, include_in_schema=False)
def regenerate_jcrew() -> HTMLResponse:
    return _render_generation_page("J.Crew", _generate_jcrew_markdown)


@app.get("/cozyknits/generate", response_class=HTMLResponse, include_in_schema=False)
def regenerate_cozy() -> HTMLResponse:
    return _render_generation_page("Cozy Knits", _generate_cozy_markdown)


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


@app.get("/generate", response_class=HTMLResponse, include_in_schema=False)
def show_generation_form() -> HTMLResponse:
    return HTMLResponse(_render_generation_form())


@app.post("/generate", response_class=HTMLResponse, include_in_schema=False)
async def handle_generation_form(request: Request) -> HTMLResponse:
    form = await request.form()
    site = form.get("site", "jcrew")
    source = (form.get("source") or "").strip()
    output = (form.get("output") or "").strip()
    title = (form.get("title") or "").strip()
    limit_raw = (form.get("limit") or "").strip()
    limit_value: int | None = None
    error = None
    markdown = None
    message = None

    try:
        if not source:
            source = _stringify_path(SITE_CONFIGS[site]["default_source"])
        if not output:
            output = _stringify_path(SITE_CONFIGS[site]["default_output"])
        if not title:
            title = SITE_CONFIGS[site]["default_title"]
        if limit_raw:
            limit_value = int(limit_raw)
        markdown = _generate_custom_markdown(site, source, output, title, limit_value)
        line_count = markdown.count("\n") + (1 if markdown else 0)
        message = f"Generated {line_count} lines and wrote {output}."
    except ValueError as exc:
        error = str(exc)
    except FileNotFoundError as exc:
        error = f"Missing file: {exc}"
    except Exception as exc:  # pragma: no cover - safety net
        error = f"Generation failed: {exc}"

    return HTMLResponse(
        _render_generation_form(
            site=site,
            source=source,
            output=output,
            title=title,
            limit=limit_raw,
            message=message,
            error=error,
            markdown=markdown,
        )
    )
