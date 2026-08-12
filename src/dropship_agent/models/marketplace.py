from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourcePlatform = Literal["amazon", "ebay", "aliexpress", "supplier_network"]


class UniversalMarketplaceItem(BaseModel):
    """Normalizes volatile multi-channel data into a single format for AI evaluation."""

    model_config = ConfigDict(extra="forbid")

    source_platform: str = Field(..., description="e.g., 'amazon', 'ebay', 'aliexpress'")
    external_id: str = Field(..., description="The unique product ID (ASIN, ItemID, etc.)")
    title: str
    current_retail_price: float
    currency: str = "USD"
    availability_status: bool
    stock_count: int | None = None
    competitor_count: int = 0
    trust_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Normalized score from 0.0 to 1.0 evaluating seller or product metrics",
    )
    raw_payload_dump: dict[str, Any] = Field(
        default_factory=dict, description="Preserves original structural data for debugging"
    )
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class AmazonRawProduct(BaseModel):
    """Loosely-typed shape of a Rainforest API (or equivalent) Amazon product payload."""

    model_config = ConfigDict(extra="allow")

    asin: str
    title: str
    price: dict[str, Any] | None = None
    rating: float | None = None
    ratings_total: int | None = None
    bestsellers_rank: list[dict[str, Any]] | None = None
    availability: dict[str, Any] | None = None
    buybox_winner: dict[str, Any] | None = None
    offers: list[dict[str, Any]] | None = None


class EbayRawItem(BaseModel):
    """Loosely-typed shape of an eBay Browse/Shopping API item payload."""

    model_config = ConfigDict(extra="allow")

    item_id: str = Field(..., alias="itemId")
    title: str
    price: dict[str, Any] | None = None
    seller: dict[str, Any] | None = None
    condition: str | None = None
    item_web_url: str | None = Field(default=None, alias="itemWebUrl")
    estimated_availabilities: list[dict[str, Any]] | None = Field(
        default=None, alias="estimatedAvailabilities"
    )
