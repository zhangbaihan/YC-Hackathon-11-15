from __future__ import annotations

"""Parser for the Cozy Knits Co. Netlify storefront."""

from pathlib import Path
import json
import re
from typing import List

from app.schemas import Product


class EffulgentParser:
    """Parse the bundled product data from the demo Netlify storefront."""

    BASE_URL = "https://effulgent-kataifi-4fc56b.netlify.app"
    PRODUCT_ARRAY_RE = re.compile(r"const\s+wf\s*=\s*(\[[^\]]+\])", re.DOTALL)
    KEY_RE = re.compile(r'(?P<prefix>[{,])\s*(?P<key>[A-Za-z0-9_]+)\s*:')

    def parse_js(self, path: str | Path, limit: int | None = None) -> List[Product]:
        """Parse the compiled JS bundle that contains the product array."""

        text = Path(path).read_text(encoding="utf-8")
        entries = self._extract_entries(text)
        products = [self._to_product(entry) for entry in entries]
        if limit is not None:
            products = products[:limit]
        return products

    def parse_file(self, path: str | Path, limit: int | None = None) -> List[Product]:
        """Compatibility shim so the parser plugs into CommercePipeline."""

        return self.parse_js(path, limit=limit)

    def _extract_entries(self, text: str) -> List[dict]:
        match = self.PRODUCT_ARRAY_RE.search(text)
        if not match:
            raise ValueError("Unable to locate product array (wf) inside the JS bundle.")

        blob = match.group(1)
        json_blob = self.KEY_RE.sub(self._quote_keys, blob)
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError as exc:  # pragma: no cover - sanity fallback
            raise ValueError("Failed to decode Netlify product payload.") from exc

        if not isinstance(parsed, list):
            raise ValueError("Expected a list of products in the Netlify payload.")
        return parsed

    def _quote_keys(self, match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        key = match.group("key")
        return f'{prefix} "{key}":'

    def _to_product(self, data: dict) -> Product:
        name = data.get("name") or f"Product {data.get('id', 'N/A')}"
        description = data.get("description") or name
        price = float(data.get("price") or 0.0)
        url = f"{self.BASE_URL}/#product-{data.get('id', 0)}"

        tags = self._build_tags(data)
        metadata = self._build_metadata(data)

        return Product(
            name=name.strip(),
            description=description.strip(),
            price=price,
            currency="USD",
            url=url,
            tags=tags,
            availability="in_stock",
            metadata=metadata,
        )

    def _build_tags(self, data: dict) -> List[str]:
        tags: List[str] = []

        category = (data.get("category") or "").strip()
        if category:
            tags.append(category.lower())

        for color in data.get("colors") or []:
            color_name = (color or "").strip()
            if color_name:
                tags.append(color_name.lower())

        return tags

    def _build_metadata(self, data: dict) -> dict[str, str]:
        metadata: dict[str, str] = {}
        mappings = {
            "id": data.get("id"),
            "image": data.get("image"),
            "rating": data.get("rating"),
            "reviews": data.get("reviews"),
            "sizes": ", ".join(data.get("sizes") or []),
        }

        for key, value in mappings.items():
            if value or value == 0:
                metadata[key] = str(value)
        return metadata
