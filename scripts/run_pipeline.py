#!/usr/bin/env python
"""CLI entrypoint to run the autonomous dropshipping LangGraph pipeline once.

Usage:
    python scripts/run_pipeline.py --asin B0EXAMPLE --ebay-item-id v1|123456789|0
    python scripts/run_pipeline.py --dry-run   # graph wiring smoke test, no keys needed
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Any

from dropship_agent.agents import (
    DynamicListingAgent,
    RealLifeValidationAgent,
    StorefrontSyncAgent,
    SupplierSourcingAgent,
    TrendScraperAgent,
)
from dropship_agent.config import get_settings
from dropship_agent.graph import build_pipeline_graph
from dropship_agent.logging_utils import configure_logging, get_logger
from dropship_agent.models.listing import ListingDraft
from dropship_agent.storefront.base_connector import StorefrontConnector


class _FakeGeminiClient:
    async def generate(self, prompt: str, *, temperature: float = 0.3) -> str:
        return "[]"


class _FakeAnthropicClient:
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return '{"confidence": 0.8, "rationale": "dry-run stub"}'


class _FakeAmazonClient:
    async def get_product(self, asin: str, **kwargs: Any) -> dict[str, Any]:
        return {"product": {"asin": asin, "title": "Dry-run product", "price": {"value": 19.99}}}


class _FakeEbayClient:
    async def get_item(self, item_id: str) -> dict[str, Any]:
        return {
            "itemId": item_id,
            "title": "Dry-run item",
            "price": {"value": 18.5, "currency": "USD"},
        }


class _FakeStorefrontConnector(StorefrontConnector):
    async def upsert_listing(self, listing: ListingDraft) -> dict[str, Any]:
        return {"status": "dry-run-ok", "title": listing.title}

    async def update_price(self, external_id: str, new_price: float) -> dict[str, Any]:
        return {"status": "dry-run-ok"}

    async def update_inventory(self, external_id: str, quantity: int) -> dict[str, Any]:
        return {"status": "dry-run-ok"}


async def run(asin: str | None, ebay_item_id: str | None, dry_run: bool) -> None:
    settings = get_settings()
    configure_logging(settings.log_dir, settings.log_level)
    log = get_logger("run_pipeline")

    if dry_run:
        gemini_client: Any = _FakeGeminiClient()
        anthropic_client: Any = _FakeAnthropicClient()
        amazon_client: Any = _FakeAmazonClient()
        ebay_client: Any = _FakeEbayClient()
        connectors: list[StorefrontConnector] = [_FakeStorefrontConnector()]
    else:
        from dropship_agent.clients import AmazonClient, AnthropicClient, EbayClient, GeminiClient
        from dropship_agent.storefront import ShopifyConnector

        gemini_client = GeminiClient(settings)
        anthropic_client = AnthropicClient(settings)
        amazon_client = AmazonClient(settings)
        ebay_client = EbayClient(settings)
        connectors = [ShopifyConnector(settings)]

    graph = build_pipeline_graph(
        trend_scraper=TrendScraperAgent(gemini_client),
        validator=RealLifeValidationAgent(anthropic_client, amazon_client, ebay_client),
        supplier_sourcer=SupplierSourcingAgent(anthropic_client),
        listing_agent=DynamicListingAgent(anthropic_client),
        storefront_sync=StorefrontSyncAgent(connectors),
    )

    initial_state = {
        "candidate_asin": asin or "",
        "candidate_ebay_item_id": ebay_item_id or "",
        "supplier_candidates": [],
        "retry_count": 0,
        "max_retries": 2,
    }
    log.info("pipeline.run.start", dry_run=dry_run)
    final_state = await graph.ainvoke(initial_state)
    log.info("pipeline.run.complete", result_keys=list(final_state.keys()))
    print(final_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the dropshipping agent pipeline once.")
    parser.add_argument("--asin", default=None, help="Real Amazon ASIN to validate against")
    parser.add_argument(
        "--ebay-item-id", default=None, help="Real eBay item ID to validate against"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Use fake clients; no network or API keys required"
    )
    args = parser.parse_args()
    asyncio.run(run(args.asin, args.ebay_item_id, args.dry_run))


if __name__ == "__main__":
    main()
