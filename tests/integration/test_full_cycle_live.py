from __future__ import annotations

import pytest

from dropship_agent.clients import AmazonClient, AnthropicClient, EbayClient, GeminiClient
from dropship_agent.config import get_settings

pytestmark = pytest.mark.live


@pytest.fixture
def live_settings():
    settings = get_settings()
    required = (
        settings.anthropic_api_key,
        settings.google_api_key,
        settings.rainforest_api_key,
        settings.ebay_app_id,
        settings.ebay_client_secret,
        settings.test_amazon_asin,
        settings.test_ebay_item_id,
    )
    if not all(required):
        pytest.skip("Full live credential set not configured; skipping end-to-end live cycle test")
    return settings


async def test_real_life_validation_agent_against_live_payloads(live_settings) -> None:
    """Runs RealLifeValidationAgent against a real ASIN and eBay item ID end-to-end.

    This is the integration cycle required by the project spec: real ASINs/item IDs,
    normalized through the shared Pydantic schema, reasoned over by Claude 3.5 Sonnet.
    """
    from dropship_agent.agents.real_life_validation_agent import RealLifeValidationAgent

    anthropic_client = AnthropicClient(live_settings)
    amazon_client = AmazonClient(live_settings)
    ebay_client = EbayClient(live_settings)
    agent = RealLifeValidationAgent(anthropic_client, amazon_client, ebay_client)

    try:
        result = await agent.run(
            {
                "candidate_asin": live_settings.test_amazon_asin,
                "candidate_ebay_item_id": live_settings.test_ebay_item_id,
            }
        )
        assert "validated_items" in result
        assert len(result["validated_items"]) == 2
        assert 0.0 <= result["validation_confidence"] <= 1.0
    finally:
        await amazon_client.aclose()
        await ebay_client.aclose()


async def test_gemini_trend_extraction_smoke(live_settings) -> None:
    """Sanity-checks the Gemini 1.5 Flash integration used by TrendScraperAgent."""
    client = GeminiClient(live_settings)
    response = await client.generate("Reply with exactly the word: ok")
    assert isinstance(response, str)
    assert len(response) > 0
