from __future__ import annotations

from typing import Any

from dropship_agent.clients.ebay_client import EbayClient
from dropship_agent.config import Settings
from dropship_agent.models.listing import ListingDraft
from dropship_agent.storefront.base_connector import StorefrontConnector


class EbayConnector(StorefrontConnector):
    """Syncs listing state to eBay via the Sell Inventory REST API.

    Reuses EbayClient's OAuth handling for authenticated calls against the Sell APIs
    (which require a different scope than the public Browse API used for validation).
    """

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        self._client = EbayClient(settings, max_retries=max_retries)

    async def upsert_listing(self, listing: ListingDraft) -> dict[str, Any]:
        token = await self._client._get_access_token()
        response = await self._client._request(
            "PUT",
            f"/sell/inventory/v1/inventory_item/{listing.source_external_id}",
            json={
                "product": {
                    "title": listing.title,
                    "description": listing.description_html,
                    "imageUrls": listing.images,
                },
                "availability": {"shipToLocationAvailability": {"quantity": 1}},
            },
            headers={"Authorization": f"Bearer {token}", "Content-Language": "en-US"},
        )
        return self._client._json(response) if response.content else {"status": response.status_code}

    async def update_price(self, external_id: str, new_price: float) -> dict[str, Any]:
        token = await self._client._get_access_token()
        response = await self._client._request(
            "POST",
            "/sell/inventory/v1/offer/publish",
            json={
                "offerId": external_id,
                "pricingSummary": {"price": {"value": f"{new_price:.2f}"}},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        return self._client._json(response) if response.content else {"status": response.status_code}

    async def update_inventory(self, external_id: str, quantity: int) -> dict[str, Any]:
        token = await self._client._get_access_token()
        response = await self._client._request(
            "PUT",
            f"/sell/inventory/v1/inventory_item/{external_id}",
            json={"availability": {"shipToLocationAvailability": {"quantity": quantity}}},
            headers={"Authorization": f"Bearer {token}", "Content-Language": "en-US"},
        )
        return self._client._json(response) if response.content else {"status": response.status_code}

    async def aclose(self) -> None:
        await self._client.aclose()
