from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from dropship_agent.models.listing import ListingDraft
from dropship_agent.models.marketplace import UniversalMarketplaceItem
from dropship_agent.models.supplier import RiskScoreMatrix, SupplierProfile


class PipelineState(TypedDict, total=False):
    """Shared mutable state threaded through every LangGraph node.

    Uses `operator.add` reducers for list-valued fields so parallel/cyclic node
    executions append rather than clobber each other's results.
    """

    trend_source_urls: list[str]
    trending_candidates: Annotated[list[dict[str, Any]], operator.add]
    candidate_asin: str
    candidate_ebay_item_id: str
    validated_items: Annotated[list[UniversalMarketplaceItem], operator.add]
    supplier_candidates: Annotated[list[SupplierProfile], operator.add]
    risk_scores: Annotated[list[RiskScoreMatrix], operator.add]
    listing_drafts: Annotated[list[ListingDraft], operator.add]
    sync_results: Annotated[list[dict[str, Any]], operator.add]

    validation_confidence: float
    supplier_approved: bool
    retry_count: int
    max_retries: int
    errors: Annotated[list[str], operator.add]
