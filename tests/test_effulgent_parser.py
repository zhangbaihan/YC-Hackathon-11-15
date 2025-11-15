from __future__ import annotations

from pathlib import Path

from app.services.effulgent_parser import EffulgentParser

JS_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "assets"
    / "main-B9P2jWt9.js"
)


def test_effulgent_parser_returns_products() -> None:
    parser = EffulgentParser()
    products = parser.parse_js(JS_FIXTURE)

    assert len(products) >= 1
    first = products[0]
    assert first.url.startswith("https://effulgent-kataifi-4fc56b.netlify.app")
    assert "cashmere" in first.name.lower()
    assert "crew neck" in first.tags[0]
