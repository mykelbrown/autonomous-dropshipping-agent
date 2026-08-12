from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dropship_agent.agents import (
    DynamicListingAgent,
    RealLifeValidationAgent,
    StorefrontSyncAgent,
    SupplierSourcingAgent,
    TrendScraperAgent,
)
from dropship_agent.graph.nodes import (
    increment_retry,
    make_node,
    route_after_supplier_sourcing,
    route_after_validation,
)
from dropship_agent.models.graph_state import PipelineState


def build_pipeline_graph(
    trend_scraper: TrendScraperAgent,
    validator: RealLifeValidationAgent,
    supplier_sourcer: SupplierSourcingAgent,
    listing_agent: DynamicListingAgent,
    storefront_sync: StorefrontSyncAgent,
) -> CompiledStateGraph[PipelineState, Any, Any, Any]:
    """Wire the five agents into a cyclic LangGraph pipeline with self-correction loops.

    Flow: trend_scrape -> validate_real_life -> [loop back on low confidence] ->
    source_suppliers -> [loop back on rejected supplier] -> draft_listing -> sync_storefront.
    """
    graph = StateGraph(PipelineState)

    graph.add_node("trend_scrape", cast(Any, make_node(trend_scraper)))
    graph.add_node("validate_real_life", cast(Any, make_node(validator)))
    graph.add_node("source_suppliers", cast(Any, make_node(supplier_sourcer)))
    graph.add_node("draft_listing", cast(Any, make_node(listing_agent)))
    graph.add_node("sync_storefront", cast(Any, make_node(storefront_sync)))
    graph.add_node("increment_retry_after_validation", cast(Any, increment_retry))
    graph.add_node("increment_retry_after_sourcing", cast(Any, increment_retry))

    graph.add_edge(START, "trend_scrape")
    graph.add_edge("trend_scrape", "validate_real_life")

    graph.add_conditional_edges(
        "validate_real_life",
        route_after_validation,
        {
            "source_suppliers": "source_suppliers",
            "trend_scrape": "increment_retry_after_validation",
            "end": END,
        },
    )
    graph.add_edge("increment_retry_after_validation", "trend_scrape")

    graph.add_conditional_edges(
        "source_suppliers",
        route_after_supplier_sourcing,
        {
            "draft_listing": "draft_listing",
            "source_suppliers": "increment_retry_after_sourcing",
            "end": END,
        },
    )
    graph.add_edge("increment_retry_after_sourcing", "source_suppliers")

    graph.add_edge("draft_listing", "sync_storefront")
    graph.add_edge("sync_storefront", END)

    return graph.compile()
