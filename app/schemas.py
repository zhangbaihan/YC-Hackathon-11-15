from __future__ import annotations

"""Shared pydantic schemas for the commerce.txt service."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Product(BaseModel):
    """Normalized representation of a single product row."""

    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=4)
    price: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=5)
    url: HttpUrl
    tags: List[str] = Field(default_factory=list)
    availability: Optional[str] = None
    metadata: dict[str, str] = Field(default_factory=dict)


class FileIngestionRequest(BaseModel):
    """Request payload used by the /process/from-file endpoint."""

    path: str = Field(..., description="Path to a JSON file with a list of products.")
    title: Optional[str] = Field(
        default=None,
        description="Optional heading that will be used in the markdown output.",
    )
    max_items: Optional[int] = Field(
        default=None,
        ge=1,
        description="Limit how many items are summarized (helps keep context budgets under control).",
    )


class ProcessedResponse(BaseModel):
    """Wrapper returned by processing endpoints."""

    markdown: str
    items: List[Product]
