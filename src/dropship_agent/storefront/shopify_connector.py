from __future__ import annotations

from typing import Any

from dropship_agent.clients.base import BaseAsyncClient
from dropship_agent.config import Settings
from dropship_agent.models.listing import ListingDraft
from dropship_agent.storefront.base_connector import StorefrontConnector


class ShopifyConnector(StorefrontConnector, BaseAsyncClient):
    """Syncs listing state to a Shopify store via the Admin REST API."""

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        domain = settings.require(settings.shopify_store_domain, "SHOPIFY_STORE_DOMAIN")
        api_version = settings.shopify_api_version
        BaseAsyncClient.__init__(
            self, base_url=f"https://{domain}/admin/api/{api_version}", max_retries=max_retries
        )
        self._token = settings.require(
            settings.shopify_admin_api_token, "SHOPIFY_ADMIN_API_TOKEN"
        )

    def _headers(self) -> dict[str, str]:
        return {"X-Shopify-Access-Token": self._token, "Content-Type": "application/json"}

    async def upsert_listing(self, listing: ListingDraft) -> dict[str, Any]:
        payload = {
            "product": {
                "title": listing.title,
                "body_html": listing.description_html,
                "tags": ", ".join(listing.tags),
                "variants": [{"price": f"{listing.pricing.recommended_price:.2f}"}],
                "images": [{"src": url} for url in listing.images],
            }
        }
        response = await self._request(
            "POST", "/products.json", json=payload, headers=self._headers()
        )
        return self._json(response)

    async def update_price(self, external_id: str, new_price: float) -> dict[str, Any]:
        response = await self._request(
            "PUT",
            f"/variants/{external_id}.json",
            json={"variant": {"id": external_id, "price": f"{new_price:.2f}"}},
            headers=self._headers(),
        )
        return self._json(response)

    async def update_inventory(self, external_id: str, quantity: int) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/inventory_levels/set.json",
            json={"inventory_item_id": external_id, "available": quantity},
            headers=self._headers(),
        )
        return self._json(response)
