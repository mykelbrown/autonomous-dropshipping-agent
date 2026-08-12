from __future__ import annotations

import json

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.clients.anthropic_client import AnthropicClient
from dropship_agent.models.graph_state import PipelineState
from dropship_agent.models.listing import ListingDraft, PricingModel, SEOMetadata

_LISTING_PROMPT = """\
You are an e-commerce conversion copywriter and pricing strategist. Given the validated \
marketplace item and supplier cost below (JSON), produce a highly converting, SEO-optimized \
listing. Price it strictly within the observed competitor price floor/ceiling from the \
source data, maximizing margin without exceeding the ceiling. Respond with ONLY a JSON \
object matching this shape: \
{{"title": "<str>", "description_html": "<str>", \
"seo": {{"seo_title": "<str>", "meta_description": "<str>", "keywords": ["..."], \
"bullet_points": ["..."]}}, \
"pricing": {{"recommended_price": <float>}}, \
"images": ["..."], "tags": ["..."]}}.

VALIDATED ITEM: {item_json}
SUPPLIER BASE COST: {base_cost}
COMPETITOR PRICE FLOOR: {price_floor}
COMPETITOR PRICE CEILING: {price_ceiling}
"""


class DynamicListingAgent(BaseAgent):
    """Uses Claude 3.5 Sonnet to rewrite validated source data into an SEO-optimized listing."""

    name = "dynamic_listing_agent"

    def __init__(self, anthropic_client: AnthropicClient) -> None:
        super().__init__()
        self._claude = anthropic_client

    async def _execute(self, state: PipelineState) -> PipelineState:
        validated_items = state.get("validated_items", [])
        if not validated_items:
            return {"errors": ["dynamic_listing_agent: no validated items to draft a listing from"]}

        item = validated_items[0]
        # placeholder heuristic until real supplier cost is wired into the pipeline state
        base_cost = item.current_retail_price * 0.4
        price_floor = item.current_retail_price * 0.85
        price_ceiling = item.current_retail_price * 1.15

        response_text = await self._claude.complete(
            system_prompt=(
                "You are a rigorous e-commerce listing copywriter and pricing strategist."
            ),
            user_prompt=_LISTING_PROMPT.format(
                item_json=item.model_dump_json(),
                base_cost=base_cost,
                price_floor=price_floor,
                price_ceiling=price_ceiling,
            ),
        )

        try:
            parsed = json.loads(response_text)
            recommended_price = float(parsed["pricing"]["recommended_price"])
            margin_pct = (
                (recommended_price - base_cost) / recommended_price if recommended_price else 0.0
            )
            draft = ListingDraft(
                source_external_id=item.external_id,
                title=parsed["title"],
                description_html=parsed["description_html"],
                seo=SEOMetadata(**parsed["seo"]),
                pricing=PricingModel(
                    base_cost=base_cost,
                    competitor_price_floor=price_floor,
                    competitor_price_ceiling=price_ceiling,
                    recommended_price=recommended_price,
                    margin_pct=margin_pct,
                ),
                images=parsed.get("images", []),
                tags=parsed.get("tags", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self._log.warning(
                "dynamic_listing.parse_failed", error=str(exc), raw_preview=response_text[:200]
            )
            return {"errors": [f"dynamic_listing_agent: failed to parse listing draft: {exc}"]}

        return {"listing_drafts": [draft]}
