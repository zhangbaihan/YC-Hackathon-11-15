from __future__ import annotations

"""Parser for extracting product data from J.Crew product listing pages."""

from pathlib import Path
import json
import re
from typing import List, Sequence

from app.schemas import Product


class JCrewPlpParser:
    """Parses the server-rendered __NEXT_DATA__ payload from J.Crew PLP pages."""

    NEXT_DATA_RE = re.compile(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
    )
    BASE_URL = "https://www.jcrew.com"
    _CATEGORY_STOP_WORDS = {"mens", "women", "categories", "clothing"}

    def parse_file(self, path: str | Path, limit: int | None = None) -> List[Product]:
        """Convenience helper that reads HTML from disk before parsing."""

        html = Path(path).read_text(encoding="utf-8")
        return self.parse_html(html, limit=limit)

    def parse_html(self, html: str, limit: int | None = None) -> List[Product]:
        """Parse raw HTML text into normalized Product schemas."""

        next_data = self._extract_next_payload(html)
        entries = self._extract_product_entries(next_data)
        products = [self._to_product(entry) for entry in entries]
        if limit is not None:
            products = products[:limit]
        return products

    def _extract_next_payload(self, html: str) -> dict:
        match = self.NEXT_DATA_RE.search(html)
        if not match:
            raise ValueError("Unable to locate __NEXT_DATA__ script in supplied HTML.")
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
            raise ValueError("Failed to decode __NEXT_DATA__ payload.") from exc

    def _extract_product_entries(self, payload: dict) -> List[dict]:
        initial_state = payload.get("props", {}).get("initialState")
        if not initial_state:
            raise ValueError("Initial state missing from __NEXT_DATA__ payload.")

        array_state = initial_state.get("array", {})
        product_array = array_state.get("data", {}).get("productArray")
        if not product_array:
            raise ValueError("productArray key missing from J.Crew payload.")

        product_lists: Sequence[dict] = product_array.get("productList") or []
        entries: List[dict] = []
        for block in product_lists:
            entries.extend(block.get("products") or [])

        if not entries:
            raise ValueError("No product entries discovered in J.Crew payload.")
        return entries

    def _to_product(self, data: dict) -> Product:
        name = data.get("productDescription") or data.get("productCode") or "Product"
        description = data.get("promoMessageOverride") or name
        price = self._resolve_price(data)
        url = self._resolve_url(data.get("url") or "")

        return Product(
            name=name.strip(),
            description=description.strip(),
            price=price,
            currency="USD",
            url=url,
            tags=self._build_tags(data),
            availability=data.get("extendedSize"),
            metadata=self._build_metadata(data),
        )

    def _resolve_price(self, data: dict) -> float:
        search_price = data.get("searchPrice")
        if search_price:
            return float(search_price)

        list_price = data.get("listPrice") or {}
        amount = list_price.get("amount")
        if amount is not None:
            return float(amount)
        return 0.0

    def _resolve_url(self, path: str) -> str:
        path = path.strip()
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.BASE_URL}{path}"

    def _build_tags(self, data: dict) -> List[str]:
        tags: List[str] = []

        category = data.get("primaryCategoryId") or ""
        for part in category.split("|"):
            normalized = part.strip()
            if normalized and normalized.lower() not in self._CATEGORY_STOP_WORDS:
                tags.append(normalized.lower().replace("-", " "))

        for color in data.get("colors") or []:
            color_name = (color.get("colorName") or "").strip()
            if color_name:
                tags.append(color_name.lower())

        badge_label = (data.get("badge") or {}).get("label")
        if badge_label:
            tags.append(badge_label.lower())

        seen: set[str] = set()
        unique_tags: List[str] = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        return unique_tags

    def _build_metadata(self, data: dict) -> dict[str, str]:
        metadata: dict[str, str] = {}
        mappings = {
            "product_code": data.get("productCode"),
            "primary_category": data.get("primaryCategoryId"),
            "badge": (data.get("badge") or {}).get("label"),
            "list_price": (data.get("listPrice") or {}).get("formatted"),
            "search_price": str(data.get("searchPrice")) if data.get("searchPrice") else None,
            "url_path": data.get("url"),
            "rating": str(data.get("bvAverageRating")) if data.get("bvAverageRating") else None,
            "reviews": str(data.get("bvReviewCount")) if data.get("bvReviewCount") else None,
        }

        for key, value in mappings.items():
            if value:
                metadata[key] = str(value)
        return metadata
