from __future__ import annotations

from pathlib import Path

from app.services.jcrew_parser import JCrewPlpParser

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "jcrew_mens_sweaters.html"


def test_parser_extracts_products() -> None:
    parser = JCrewPlpParser()
    products = parser.parse_file(FIXTURE)

    assert products, "the parser should surface the PLP products"
    first = products[0]

    assert first.name
    assert first.price >= 0
    assert first.url.startswith("https://www.jcrew.com")
    assert first.currency == "USD"
    assert "sweaters" in first.tags
