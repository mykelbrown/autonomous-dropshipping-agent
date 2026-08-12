from __future__ import annotations

from dropship_agent.normalization.mappers import amazon_to_universal, ebay_to_universal


def test_amazon_to_universal_maps_core_fields() -> None:
    raw = {
        "product": {
            "asin": "B0EXAMPLE",
            "title": "Wireless Earbuds",
            "buybox_winner": {"price": {"value": 29.99, "currency": "USD"}},
            "rating": 4.5,
            "availability": {"raw": "In Stock."},
            "offers": [{"price": 30.5}, {"price": 28.0}],
        }
    }

    item = amazon_to_universal(raw)

    assert item.source_platform == "amazon"
    assert item.external_id == "B0EXAMPLE"
    assert item.title == "Wireless Earbuds"
    assert item.current_retail_price == 29.99
    assert item.currency == "USD"
    assert item.availability_status is True
    assert item.competitor_count == 2
    assert item.trust_score == 0.9
    assert item.raw_payload_dump == raw


def test_ebay_to_universal_maps_core_fields() -> None:
    raw = {
        "itemId": "v1|123456789|0",
        "title": "Bluetooth Speaker",
        "price": {"value": 45.0, "currency": "USD"},
        "seller": {"feedbackPercentage": "98.5"},
        "estimatedAvailabilities": [
            {"estimatedAvailableQuantity": 12, "estimatedAvailabilityStatus": "IN_STOCK"}
        ],
    }

    item = ebay_to_universal(raw)

    assert item.source_platform == "ebay"
    assert item.external_id == "v1|123456789|0"
    assert item.current_retail_price == 45.0
    assert item.availability_status is True
    assert item.stock_count == 12
    assert item.trust_score == 0.985


def test_ebay_to_universal_handles_missing_availability() -> None:
    raw = {"itemId": "abc", "title": "No availability info", "price": {"value": 10.0}}

    item = ebay_to_universal(raw)

    assert item.availability_status is True
    assert item.stock_count is None
    assert item.trust_score == 0.0
