from __future__ import annotations

import json

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.clients.amazon_client import AmazonClient
from dropship_agent.clients.anthropic_client import AnthropicClient
from dropship_agent.clients.ebay_client import EbayClient
from dropship_agent.models.graph_state import PipelineState
from dropship_agent.normalization.mappers import amazon_to_universal, ebay_to_universal

_VALIDATION_PROMPT = """\
You are validating a trend candidate against real marketplace data. Given the normalized \
Amazon and eBay listings below (JSON), assess: live sales-rank plausibility, competitor \
pricing pressure, review sentiment implied by trust_score, and demand velocity. Respond \
with ONLY a JSON object: {{"confidence": <0.0-1.0>, "rationale": "<one paragraph>"}}.

AMAZON: {amazon_json}
EBAY: {ebay_json}
"""


class RealLifeValidationAgent(BaseAgent):
    """Uses Claude 3.5 Sonnet plus live Amazon/eBay data to validate a trend candidate."""

    name = "real_life_validation_agent"

    def __init__(
        self,
        anthropic_client: AnthropicClient,
        amazon_client: AmazonClient,
        ebay_client: EbayClient,
    ) -> None:
        super().__init__()
        self._claude = anthropic_client
        self._amazon = amazon_client
        self._ebay = ebay_client

    async def _execute(self, state: PipelineState) -> PipelineState:
        asin = state.get("candidate_asin")
        ebay_item_id = state.get("candidate_ebay_item_id")

        validated_items = []
        if asin:
            raw = await self._amazon.get_product(asin)
            validated_items.append(amazon_to_universal(raw))
        if ebay_item_id:
            raw = await self._ebay.get_item(ebay_item_id)
            validated_items.append(ebay_to_universal(raw))

        amazon_json = (
            validated_items[0].model_dump_json() if asin and validated_items else "null"
        )
        ebay_json = (
            validated_items[-1].model_dump_json()
            if ebay_item_id and validated_items
            else "null"
        )

        analysis_text = await self._claude.complete(
            system_prompt="You are a rigorous e-commerce market validation analyst.",
            user_prompt=_VALIDATION_PROMPT.format(amazon_json=amazon_json, ebay_json=ebay_json),
        )

        try:
            analysis = json.loads(analysis_text)
            confidence = float(analysis.get("confidence", 0.0))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._log.warning(
                "real_life_validation.parse_failed", raw_preview=analysis_text[:200]
            )
            confidence = 0.0

        return {
            "validated_items": validated_items,
            "validation_confidence": confidence,
        }
