from __future__ import annotations

from collections.abc import Awaitable, Callable

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.models.graph_state import PipelineState

VALIDATION_CONFIDENCE_THRESHOLD = 0.6


def make_node(agent: BaseAgent) -> Callable[[PipelineState], Awaitable[PipelineState]]:
    """Adapt a BaseAgent into a LangGraph-compatible async node function."""

    async def _node(state: PipelineState) -> PipelineState:
        return await agent.run(state)

    _node.__name__ = agent.name
    return _node


def route_after_validation(state: PipelineState) -> str:
    """Self-correction edge: low-confidence validation loops back to trend scraping."""
    confidence = state.get("validation_confidence", 0.0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if confidence >= VALIDATION_CONFIDENCE_THRESHOLD:
        return "source_suppliers"
    if retry_count >= max_retries:
        return "end"
    return "trend_scrape"


def route_after_supplier_sourcing(state: PipelineState) -> str:
    """Self-correction edge: unapproved suppliers loop back to re-source, bounded by retries."""
    approved = state.get("supplier_approved", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if approved:
        return "draft_listing"
    if retry_count >= max_retries:
        return "end"
    return "source_suppliers"


def increment_retry(state: PipelineState) -> PipelineState:
    return {"retry_count": state.get("retry_count", 0) + 1}
