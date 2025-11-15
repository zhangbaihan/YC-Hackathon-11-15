from __future__ import annotations

"""CLI entry point for generating the commerce.txt artifact via the pipeline."""

import argparse
from pathlib import Path

from app.services.pipeline import CommercePipeline
from app.services.jcrew_parser import JCrewPlpParser
from app.services.effulgent_parser import EffulgentParser
from app.services.compression import MarkdownCompressor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the commerce.txt markdown file.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/jcrew_mens_sweaters.html"),
        help="Path to the saved source snapshot (HTML or JS).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/commerce_jcrew.txt"),
        help="Destination markdown file (defaults to data/commerce_jcrew.txt).",
    )
    parser.add_argument(
        "--title",
        default="J.Crew men sweaters",
        help="Heading used for the generated markdown.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for how many products to include.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parser = JCrewPlpParser()
    if args.source.suffix == ".js":
        parser = EffulgentParser()
    pipeline = CommercePipeline(parser=parser, compressor=MarkdownCompressor())

    markdown = pipeline.write_markdown(
        args.source,
        args.output,
        title=args.title,
        limit=args.limit,
    )
    print(f"Wrote {args.output} with {len(markdown.splitlines())} lines.")  # noqa: T201


if __name__ == "__main__":
    main()
