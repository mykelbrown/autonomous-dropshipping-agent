from __future__ import annotations

from typing import Any

from dropship_agent.agents.dynamic_listing_agent import DynamicListingAgent
from dropship_agent.agents.storefront_sync_agent import StorefrontSyncAgent
from dropship_agent.agents.supplier_sourcing_agent import SupplierSourcingAgent
from dropship_agent.agents.trend_scraper_agent import TrendScraperAgent
from dropship_agent.models.listing import ListingDraft
from dropship_agent.models.marketplace import UniversalMarketplaceItem
from dropship_agent.models.supplier import SupplierProfile
from dropship_agent.storefront.base_connector import StorefrontConnector


class _StubGeminiClient:
    def __init__(self, response: str) -> None:
        self._response = response

    async def generate(self, prompt: str, *, temperature: float = 0.3) -> str:
        return self._response


class _StubAnthropicClient:
    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return self._response


class _StubConnector(StorefrontConnector):
    def __init__(self) -> None:
        self.upserted: list[ListingDraft] = []

    async def upsert_listing(self, listing: ListingDraft) -> dict[str, Any]:
        self.upserted.append(listing)
        return {"status": "ok"}

    async def update_price(self, external_id: str, new_price: float) -> dict[str, Any]:
        return {"status": "ok"}

    async def update_inventory(self, external_id: str, quantity: int) -> dict[str, Any]:
        return {"status": "ok"}


async def test_trend_scraper_agent_parses_gemini_json() -> None:
    agent = TrendScraperAgent(_StubGeminiClient('[{"product_name": "Widget"}]'))
    result = await agent.run({"trend_source_urls": []})
    assert result["trending_candidates"] == [{"product_name": "Widget"}]


async def test_trend_scraper_agent_handles_bad_json_gracefully() -> None:
    agent = TrendScraperAgent(_StubGeminiClient("not json"))
    result = await agent.run({"trend_source_urls": []})
    assert result["trending_candidates"] == []


async def test_supplier_sourcing_agent_approves_low_risk_supplier() -> None:
    response = (
        '{"shipping_risk": 0.1, "stock_risk": 0.1, "dispute_risk": 0.05, '
        '"overall_risk_score": 0.1, "recommendation": "approve", "rationale": "solid"}'
    )
    agent = SupplierSourcingAgent(_StubAnthropicClient(response))
    supplier = SupplierProfile(
        supplier_id="sup-1",
        name="Acme Supply",
        platform="aliexpress",
        shipping_latency_days_avg=5.0,
        shipping_latency_variance_days=1.0,
        stock_level=500,
        dispute_rate=0.01,
        on_time_delivery_rate=0.97,
        years_active=3.0,
    )
    result = await agent.run({"supplier_candidates": [supplier]})
    assert result["supplier_approved"] is True
    assert result["risk_scores"][0].recommendation == "approve"


async def test_dynamic_listing_agent_builds_draft() -> None:
    response = (
        '{"title": "Great Widget", "description_html": "<p>desc</p>", '
        '"seo": {"seo_title": "Great Widget", "meta_description": "desc", '
        '"keywords": ["widget"], "bullet_points": ["fast"]}, '
        '"pricing": {"recommended_price": 25.0}, "images": [], "tags": ["new"]}'
    )
    agent = DynamicListingAgent(_StubAnthropicClient(response))
    item = UniversalMarketplaceItem(
        source_platform="amazon",
        external_id="B0EXAMPLE",
        title="Widget",
        current_retail_price=20.0,
        availability_status=True,
    )
    result = await agent.run({"validated_items": [item]})
    draft = result["listing_drafts"][0]
    assert draft.title == "Great Widget"
    assert draft.pricing.recommended_price == 25.0


async def test_storefront_sync_agent_pushes_to_all_connectors() -> None:
    connector = _StubConnector()
    agent = StorefrontSyncAgent([connector])
    draft = ListingDraft(
        source_external_id="B0EXAMPLE",
        title="Great Widget",
        description_html="<p>desc</p>",
        seo={"seo_title": "t", "meta_description": "d", "keywords": [], "bullet_points": []},
        pricing={
            "base_cost": 10.0,
            "competitor_price_floor": 15.0,
            "competitor_price_ceiling": 30.0,
            "recommended_price": 25.0,
            "margin_pct": 0.6,
        },
    )
    result = await agent.run({"listing_drafts": [draft]})
    assert len(result["sync_results"]) == 1
    assert connector.upserted == [draft]
