from __future__ import annotations

import base64
import time
from typing import Any

from dropship_agent.clients.base import BaseAsyncClient
from dropship_agent.config import Settings

_PRODUCTION_BASE = "https://api.ebay.com"
_SANDBOX_BASE = "https://api.sandbox.ebay.com"


class EbayClient(BaseAsyncClient):
    """Async client for the official eBay Developer REST APIs (OAuth client-credentials flow)."""

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        base_url = _PRODUCTION_BASE if settings.ebay_environment == "production" else _SANDBOX_BASE
        super().__init__(base_url=base_url, max_retries=max_retries)
        self._app_id = settings.require(settings.ebay_app_id, "EBAY_APP_ID")
        self._client_secret = settings.require(settings.ebay_client_secret, "EBAY_CLIENT_SECRET")
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        credentials = base64.b64encode(f"{self._app_id}:{self._client_secret}".encode()).decode()
        response = await self._request(
            "POST",
            "/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        payload = self._json(response)
        self._token = payload["access_token"]
        self._token_expires_at = time.monotonic() + payload.get("expires_in", 7200) - 60
        return self._token

    async def get_item(self, item_id: str) -> dict[str, Any]:
        token = await self._get_access_token()
        response = await self._request(
            "GET",
            f"/buy/browse/v1/item/{item_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
        )
        return self._json(response)

    async def search_items(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        token = await self._get_access_token()
        response = await self._request(
            "GET",
            "/buy/browse/v1/item_summary/search",
            params={"q": query, "limit": str(limit)},
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
        )
        return self._json(response)
