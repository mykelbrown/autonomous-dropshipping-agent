from __future__ import annotations

from typing import Any

from dropship_agent.models.marketplace import UniversalMarketplaceItem


def amazon_to_universal(raw: dict[str, Any]) -> UniversalMarketplaceItem:
    """Map a raw Rainforest API `product` payload into UniversalMarketplaceItem."""
    product = raw.get("product", raw)
    price_info = product.get("buybox_winner", {}).get("price") or product.get("price") or {}
    offers = product.get("offers") or []
    availability = product.get("availability", {}) or {}

    return UniversalMarketplaceItem(
        source_platform="amazon",
        external_id=product.get("asin", ""),
        title=product.get("title", ""),
        current_retail_price=float(price_info.get("value", 0.0) or 0.0),
        currency=price_info.get("currency", "USD"),
        availability_status="in stock" in str(availability.get("raw", "")).lower(),
        stock_count=None,
        competitor_count=len(offers),
        trust_score=min(1.0, (product.get("rating") or 0.0) / 5.0),
        raw_payload_dump=raw,
    )


def ebay_to_universal(raw: dict[str, Any]) -> UniversalMarketplaceItem:
    """Map a raw eBay Browse API `item` payload into UniversalMarketplaceItem."""
    price_info = raw.get("price") or {}
    availabilities = raw.get("estimatedAvailabilities") or []
    stock_count = None
    availability_status = True
    if availabilities:
        first = availabilities[0]
        stock_count = first.get("estimatedAvailableQuantity")
        availability_status = str(first.get("estimatedAvailabilityStatus", "")).upper() in {
            "IN_STOCK",
            "LIMITED_STOCK",
        }

    seller = raw.get("seller") or {}
    feedback_pct = seller.get("feedbackPercentage")
    trust_score = float(feedback_pct) / 100.0 if feedback_pct is not None else 0.0

    return UniversalMarketplaceItem(
        source_platform="ebay",
        external_id=raw.get("itemId", ""),
        title=raw.get("title", ""),
        current_retail_price=float(price_info.get("value", 0.0) or 0.0),
        currency=price_info.get("currency", "USD"),
        availability_status=availability_status,
        stock_count=stock_count,
        competitor_count=0,
        trust_score=trust_score,
        raw_payload_dump=raw,
    )


def supplier_to_universal(raw: dict[str, Any]) -> UniversalMarketplaceItem:
    """Map a raw supplier-network product listing into UniversalMarketplaceItem."""
    return UniversalMarketplaceItem(
        source_platform="supplier_network",
        external_id=str(raw.get("id", raw.get("sku", ""))),
        title=raw.get("title", raw.get("name", "")),
        current_retail_price=float(raw.get("price", 0.0) or 0.0),
        currency=raw.get("currency", "USD"),
        availability_status=bool(
            raw.get("in_stock", raw.get("stock", 0) and raw.get("stock", 0) > 0)
        ),
        stock_count=raw.get("stock"),
        competitor_count=int(raw.get("competitor_count", 0) or 0),
        trust_score=float(raw.get("supplier_rating", 0.0) or 0.0) / 5.0,
        raw_payload_dump=raw,
    )
