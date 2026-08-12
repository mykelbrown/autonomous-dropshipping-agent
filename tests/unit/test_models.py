from __future__ import annotations

import pytest
from pydantic import ValidationError

from dropship_agent.models.marketplace import UniversalMarketplaceItem


def test_universal_marketplace_item_defaults() -> None:
    item = UniversalMarketplaceItem(
        source_platform="amazon",
        external_id="B0EXAMPLE",
        title="Example Product",
        current_retail_price=19.99,
        availability_status=True,
    )
    assert item.currency == "USD"
    assert item.stock_count is None
    assert item.competitor_count == 0
    assert item.trust_score == 0.0
    assert item.raw_payload_dump == {}


def test_universal_marketplace_item_trust_score_bounds() -> None:
    with pytest.raises(ValidationError):
        UniversalMarketplaceItem(
            source_platform="ebay",
            external_id="123",
            title="Bad trust score",
            current_retail_price=5.0,
            availability_status=True,
            trust_score=1.5,
        )


def test_universal_marketplace_item_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UniversalMarketplaceItem(
            source_platform="ebay",
            external_id="123",
            title="Extra field",
            current_retail_price=5.0,
            availability_status=True,
            unexpected_field="nope",  # type: ignore[call-arg]
        )
