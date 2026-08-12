from __future__ import annotations

from dropship_agent.clients.base import BaseAsyncClient
from dropship_agent.config import Settings


class ScrapingProxyClient(BaseAsyncClient):
    """Generic fallback for fetching arbitrary trend/product pages through a scraping proxy.

    Used by TrendScraperAgent when a target site has no official API (e.g. trending
    product feeds, social commerce signals). Defaults to ScrapingBee's render endpoint;
    swap `base_url`/`_build_params` for Bright Data's Web Unlocker API if preferred.
    """

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        super().__init__(base_url="https://app.scrapingbee.com", max_retries=max_retries)
        self._api_key = settings.require(settings.scrapingbee_api_key, "SCRAPINGBEE_API_KEY")

    async def fetch_rendered_html(self, target_url: str, *, render_js: bool = True) -> str:
        response = await self._request(
            "GET",
            "/api/v1/",
            params={
                "api_key": self._api_key,
                "url": target_url,
                "render_js": "true" if render_js else "false",
            },
        )
        return response.text
