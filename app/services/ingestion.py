from __future__ import annotations

"""Utilities for loading structured commerce data from files."""

from pathlib import Path
from typing import Iterable, List, Sequence
import json

from app.schemas import Product


class FileIngestor:
    """Read JSON files that contain a list of product dictionaries."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else None

    def _resolve_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute() and self.base_dir:
            candidate = self.base_dir / candidate
        return candidate

    def load_products(self, path: str | Path, limit: int | None = None) -> List[Product]:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        raw_text = file_path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{file_path} does not contain valid JSON") from exc

        if not isinstance(parsed, Sequence):
            raise ValueError("JSON data must be a list of product objects")

        products = [Product.model_validate(item) for item in parsed]
        if limit is not None:
            products = products[:limit]
        return products

    def load_from_iterable(self, payload: Iterable[dict], limit: int | None = None) -> List[Product]:
        """Helper for future ingestion sources (e.g. scraped results)."""

        products = [Product.model_validate(item) for item in payload]
        if limit is not None:
            products = products[:limit]
        return products
