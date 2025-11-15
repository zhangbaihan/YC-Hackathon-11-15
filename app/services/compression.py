from __future__ import annotations

"""Convert normalized products into context-optimized Markdown."""

from typing import Iterable, List

from app.schemas import Product


class MarkdownCompressor:
    """Summarizes product data into a markdown block optimized for AI agents."""

    def __init__(self, max_description_chars: int = 280) -> None:
        self.max_description_chars = max_description_chars

    def build_listing(self, products: Iterable[Product], title: str | None = None) -> str:
        normalized: List[Product] = list(products)
        if not normalized:
            return "_No products available to summarize._"

        lines: List[str] = []
        heading = title or "commerce.txt spotlight"
        lines.append(f"## {heading.strip()}")
        lines.append("")

        for idx, product in enumerate(normalized, start=1):
            desc = self._trim(product.description)
            tags = ", ".join(product.tags) if product.tags else "no tags"
            availability = f" · {product.availability}" if product.availability else ""
            price = f"{product.currency} {product.price:,.2f}" if product.currency else f"{product.price:,.2f}"

            lines.append(
                f"{idx}. [{product.name}]({product.url}) — {price}{availability}"
            )
            lines.append(f"   - {desc}")
            lines.append(f"   - tags: {tags}")
            if product.metadata:
                hint = ", ".join(f"{k}: {v}" for k, v in product.metadata.items())
                lines.append(f"   - meta: {hint}")
            lines.append("")

        return "\n".join(line.rstrip() for line in lines).strip()

    def _trim(self, text: str) -> str:
        text = text.strip()
        if len(text) <= self.max_description_chars:
            return text
        return text[: self.max_description_chars - 3].rstrip() + "..."
