from __future__ import annotations

import pytest

from dropship_agent.clients.amazon_client import AmazonClient
from dropship_agent.config import get_settings
from dropship_agent.normalization.mappers import amazon_to_universal

pytestmark = pytest.mark.live


@pytest.fixture
def live_settings():
    settings = get_settings()
    if not (settings.rainforest_api_key and settings.test_amazon_asin):
        pytest.skip("RAINFOREST_API_KEY / TEST_AMAZON_ASIN not configured; skipping live test")
    return settings


async def test_fetch_and_normalize_real_asin(live_settings) -> None:
    client = AmazonClient(live_settings)
    try:
        raw = await client.get_product(live_settings.test_amazon_asin)
        item = amazon_to_universal(raw)

        assert item.source_platform == "amazon"
        assert item.external_id == live_settings.test_amazon_asin
        assert item.title
        assert item.current_retail_price >= 0.0
    finally:
        await client.aclose()
