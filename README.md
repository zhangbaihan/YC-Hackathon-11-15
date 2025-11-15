# commerce.txt

FastAPI service that ingests product data from structured files (JSON to start, with web scraping support planned) and emits a condensed, link-rich Markdown catalog that is tailored for AI agents to read.

## Features
- File-based ingestion that validates JSON input against strongly typed schemas.
- Deterministic markdown compression that highlights price, positioning, and tags for each product.
- Extensible service layer ready for future scraping or additional enrichment steps.

## Getting started
1. Install [uv](https://github.com/astral-sh/uv) (e.g. `curl -LsSf https://astral.sh/uv/install.sh | sh`).
2. Create/activate a virtual environment (`uv venv && source .venv/bin/activate`) or let `uv run` manage one automatically.
3. Install dependencies with `uv sync --group dev` (or fall back to `pip install -e .[dev]`).
4. Serve the API with `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` or regenerate the static artifacts with `uv run python scripts/generate_commerce.py` (pass `--source data/assets/main-B9P2jWt9.js --output data/commerce_cozy_knits.txt --title "Cozy Knits Co. catalog"` for the Netlify snapshot).

## API overview
- `POST /process/from-file` — Accepts a JSON file path on disk, loads validated products, and responds with a markdown summary alongside the normalized data.
- `GET /jcrew/commerce.txt` — Generates/serves the J.Crew markdown artifact.
- `GET /cozyknits/commerce.txt` — Generates/serves the Cozy Knits (Netlify) markdown artifact.

Example request body:

```json
{
  "path": "data/sample_products.json",
  "title": "Weekly home office picks"
}
```

Example response excerpt:

```json
{
  "markdown": "## Weekly home office picks\n1. [FlexDesk Pro](https://example.com/desks/flexdesk-pro)...",
  "items": [
    {
      "name": "FlexDesk Pro",
      "description": "Premium sit/stand desk",
      "price": 899.0,
      "currency": "USD",
      "url": "https://example.com/desks/flexdesk-pro",
      "tags": ["desk", "ergonomic"]
    }
  ]
}
```

## Project layout
- `app/main.py` — FastAPI wiring and request handlers (including the `commerce.txt` endpoint).
- `app/schemas.py` — Pydantic representations shared between layers.
- `app/services/ingestion.py` — File ingestion utilities.
- `app/services/compression.py` — Markdown compression pipeline.
- `app/services/jcrew_parser.py` — Parser that extracts products from a saved J.Crew PLP HTML page.
- `app/services/effulgent_parser.py` — Parser that reads the Cozy Knits (mockup-merchant) JS bundle.
- `app/services/pipeline.py` — Glue helpers that parse a PLP snapshot and emit markdown.
- `scripts/generate_commerce.py` — CLI helper (`uv run python scripts/generate_commerce.py`) to rebuild artifacts.
- `data/sample_products.json` — Example data stub for quick manual testing.
- `data/jcrew_mens_sweaters.html` — Saved source HTML for the current J.Crew mens sweaters category.
- `data/commerce_jcrew.txt` — The generated markdown served as `/jcrew/commerce.txt`.
- `data/commerce_cozy_knits.txt` — The generated markdown served as `/cozyknits/commerce.txt`.
- `data/mockup_merchant.html` — Saved Cozy Knits landing page (for reference).
- `data/assets/mockup_app_page.js` — Bundled Cozy Knits product data consumed by `EffulgentParser`.

## Using uv for day-to-day tasks
- `uv sync --group dev` — install runtime + dev dependencies into `.venv` (or just run `uv sync` if you already have dev dependencies enabled globally).
- `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — launch the API with hot reload.
- `uv run python scripts/generate_commerce.py -- --limit 10` — regenerate `data/commerce_jcrew.txt` (pass script args after `--`; include `--source data/assets/mockup_app_page.js --output data/commerce_cozy_knits.txt` for the Cozy Knits snapshot).
- Each `/jcrew/commerce.txt` and `/cozyknits/commerce.txt` response simply streams the existing markdown artifact from `data/`, so re-run the generation script whenever the upstream source snapshot changes.
- `uv run pytest` — execute the pytest suite without manually activating the venv.

## Working with the J.Crew parser
1. Download a snapshot of a J.Crew category page (already provided at `data/jcrew_mens_sweaters.html`).
2. Use the parser directly, or regenerate the markdown with `uv run python scripts/generate_commerce.py`:

```python
from pathlib import Path
from app.services.pipeline import CommercePipeline
from app.services.jcrew_parser import JCrewPlpParser

pipeline = CommercePipeline(parser=JCrewPlpParser())
markdown = pipeline.write_markdown(
    Path("data/jcrew_mens_sweaters.html"),
    Path("data/commerce_jcrew.txt"),
    title="J.Crew men sweaters",
)
```

3. Feed the resulting `products` list (via `JCrewPlpParser`) into `MarkdownCompressor` or any other downstream consumer, or simply serve the generated `data/commerce_jcrew.txt` through the API.

Run `pytest tests/test_jcrew_parser.py tests/test_pipeline.py tests/test_effulgent_parser.py` to ensure the extractor and pipeline continue to match the upstream payload shape.

## Working with the Cozy Knits (Netlify) parser
The Cozy Knits storefront on mockup-merchant embeds its product catalog inside the compiled JS bundle located at `data/assets/mockup_app_page.js`. Use `EffulgentParser` to normalize that payload:

```python
from app.services.effulgent_parser import EffulgentParser

parser = EffulgentParser()
products = parser.parse_js("data/assets/mockup_app_page.js")
```

You can then pass `products` into `MarkdownCompressor` or your own aggregator. Run `pytest tests/test_effulgent_parser.py` whenever the upstream bundle changes to guarantee the parser still matches the embedded schema.

## Next steps
- Add scraping adapters to `app/services/ingestion.py`.
- Track provenance metadata per item for better AI transparency.
- Layer in summarization/LLM steps once the structured pipeline is stable.
# YC-Hackathon-11-15
