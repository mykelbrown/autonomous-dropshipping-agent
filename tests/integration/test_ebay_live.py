from __future__ import annotations

import pytest

from dropship_agent.clients.ebay_client import EbayClient
from dropship_agent.config import get_settings
from dropship_agent.normalization.mappers import ebay_to_universal

pytestmark = pytest.mark.live


@pytest.fixture
def live_settings():
    settings = get_settings()
    has_creds = settings.ebay_app_id and settings.ebay_client_secret and settings.test_ebay_item_id
    if not has_creds:
        pytest.skip("EBAY_APP_ID / EBAY_CLIENT_SECRET / TEST_EBAY_ITEM_ID not configured")
    return settings


async def test_fetch_and_normalize_real_item(live_settings) -> None:
    client = EbayClient(live_settings)
    try:
        raw = await client.get_item(live_settings.test_ebay_item_id)
        item = ebay_to_universal(raw)

        assert item.source_platform == "ebay"
        assert item.title
        assert item.current_retail_price >= 0.0
    finally:
        await client.aclose()
