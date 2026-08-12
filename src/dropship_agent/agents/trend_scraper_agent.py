from __future__ import annotations

import json
from typing import Any

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.clients.gemini_client import GeminiClient
from dropship_agent.clients.scraping_proxy_client import ScrapingProxyClient
from dropship_agent.models.graph_state import PipelineState

_TREND_EXTRACTION_PROMPT = """\
You are a trend-detection analyst for a dropshipping platform. Given the raw web page \
content below, extract up to 10 high-velocity consumer product signals (products with \
sudden or rising demand). For each, output a JSON object with keys: \
"product_name", "category", "estimated_search_velocity" ("rising"|"stable"|"declining"), \
"signal_source", "notes". Return ONLY a JSON array, no prose.

RAW CONTENT:
{content}
"""


class TrendScraperAgent(BaseAgent):
    """Uses Gemini 1.5 Flash to parse high-volume web/trend-feed content into candidate signals."""

    name = "trend_scraper_agent"

    def __init__(
        self,
        gemini_client: GeminiClient,
        scraping_client: ScrapingProxyClient | None = None,
    ) -> None:
        super().__init__()
        self._gemini = gemini_client
        self._scraper = scraping_client

    async def _execute(self, state: PipelineState) -> PipelineState:
        trend_urls: list[str] = state.get("trend_source_urls", []) or []
        raw_contents: list[str] = []

        if self._scraper is not None:
            for url in trend_urls:
                html = await self._scraper.fetch_rendered_html(url)
                raw_contents.append(html[:20_000])

        if not raw_contents:
            raw_contents = ["No live source configured; supply trend_source_urls in state."]

        candidates: list[dict[str, Any]] = []
        for content in raw_contents:
            prompt = _TREND_EXTRACTION_PROMPT.format(content=content)
            response_text = await self._gemini.generate(prompt)
            try:
                parsed = json.loads(response_text)
                if isinstance(parsed, list):
                    candidates.extend(parsed)
            except json.JSONDecodeError:
                self._log.warning("trend_scraper.parse_failed", raw_preview=response_text[:200])

        return {"trending_candidates": candidates}
