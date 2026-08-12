from __future__ import annotations

from typing import Any

from dropship_agent.clients.base import BaseAsyncClient
from dropship_agent.config import Settings


class AmazonClient(BaseAsyncClient):
    """Async client for live Amazon product data via the Rainforest API.

    Swap `_get_params`/base_url for Bright Data or ScrapingBee if a different
    provider is preferred; the rest of the pipeline only depends on the
    `get_product(asin)` -> raw dict contract.
    """

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        super().__init__(base_url="https://api.rainforestapi.com", max_retries=max_retries)
        self._api_key = settings.require(settings.rainforest_api_key, "RAINFOREST_API_KEY")

    async def get_product(self, asin: str, *, amazon_domain: str = "amazon.com") -> dict[str, Any]:
        response = await self._request(
            "GET",
            "/request",
            params={
                "api_key": self._api_key,
                "type": "product",
                "asin": asin,
                "amazon_domain": amazon_domain,
            },
        )
        return self._json(response)

    async def search_bestsellers(
        self, category_id: str, *, amazon_domain: str = "amazon.com"
    ) -> dict[str, Any]:
        response = await self._request(
            "GET",
            "/request",
            params={
                "api_key": self._api_key,
                "type": "bestsellers",
                "category_id": category_id,
                "amazon_domain": amazon_domain,
            },
        )
        return self._json(response)
