from __future__ import annotations

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.models.graph_state import PipelineState
from dropship_agent.storefront.base_connector import StorefrontConnector


class StorefrontSyncAgent(BaseAgent):
    """Pushes finalized listing drafts to one or more storefront connectors (Shopify, eBay, ...)."""

    name = "storefront_sync_agent"

    def __init__(self, connectors: list[StorefrontConnector]) -> None:
        super().__init__()
        self._connectors = connectors

    async def _execute(self, state: PipelineState) -> PipelineState:
        drafts = state.get("listing_drafts", [])
        if not drafts:
            return {"errors": ["storefront_sync_agent: no listing drafts to sync"]}

        sync_results = []
        for draft in drafts:
            for connector in self._connectors:
                result = await connector.upsert_listing(draft)
                sync_results.append(
                    {
                        "connector": connector.__class__.__name__,
                        "external_id": draft.source_external_id,
                        "result": result,
                    }
                )

        return {"sync_results": sync_results}
