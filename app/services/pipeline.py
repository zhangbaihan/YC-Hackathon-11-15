from __future__ import annotations

"""Pipeline helpers for producing the commerce.txt markdown artifact."""

from pathlib import Path
from typing import Optional

from app.services.jcrew_parser import JCrewPlpParser
from app.services.compression import MarkdownCompressor


class CommercePipeline:
    """Glue object that parses and compresses a PLP snapshot into markdown."""

    def __init__(
        self,
        parser: Optional[JCrewPlpParser] = None,
        compressor: Optional[MarkdownCompressor] = None,
    ) -> None:
        self.parser = parser or JCrewPlpParser()
        self.compressor = compressor or MarkdownCompressor()

    def build_markdown(
        self,
        html_path: Path,
        *,
        title: str | None = None,
        limit: int | None = None,
    ) -> str:
        products = self.parser.parse_file(html_path, limit=limit)
        return self.compressor.build_listing(products, title=title)

    def write_markdown(
        self,
        html_path: Path,
        output_path: Path,
        *,
        title: str | None = None,
        limit: int | None = None,
    ) -> str:
        markdown = self.build_markdown(html_path, title=title, limit=limit)
        output_path.write_text(markdown, encoding="utf-8")
        return markdown
