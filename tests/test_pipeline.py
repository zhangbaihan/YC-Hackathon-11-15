from __future__ import annotations

from pathlib import Path

from app.services.pipeline import CommercePipeline
from app.services.jcrew_parser import JCrewPlpParser
from app.services.compression import MarkdownCompressor

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "jcrew_mens_sweaters.html"


def test_pipeline_writes_markdown(tmp_path) -> None:
    pipeline = CommercePipeline(
        parser=JCrewPlpParser(), compressor=MarkdownCompressor()
    )
    target = tmp_path / "commerce.txt"

    markdown = pipeline.write_markdown(FIXTURE, target, title="Fixture test")

    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert content == markdown
    assert content.startswith("## Fixture test")
