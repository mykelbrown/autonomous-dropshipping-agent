from __future__ import annotations

import json

from dropship_agent.agents.base_agent import BaseAgent
from dropship_agent.clients.anthropic_client import AnthropicClient
from dropship_agent.models.graph_state import PipelineState
from dropship_agent.models.supplier import RiskScoreMatrix, SupplierProfile

_RISK_SCORING_PROMPT = """\
You are a supplier risk analyst for a dropshipping operation. Given the supplier profile \
below (JSON), compute a risk-scoring matrix. Weigh shipping latency variance heavily \
(unpredictability is worse than a slow-but-consistent supplier), factor in stock levels \
relative to expected order volume, and weight dispute rate as the strongest negative signal. \
Respond with ONLY a JSON object matching this shape: \
{{"shipping_risk": <0-1>, "stock_risk": <0-1>, "dispute_risk": <0-1>, \
"overall_risk_score": <0-1>, "recommendation": "approve"|"reject"|"monitor", \
"rationale": "<text>"}}.

SUPPLIER PROFILE: {supplier_json}
"""

REJECT_THRESHOLD = 0.65


class SupplierSourcingAgent(BaseAgent):
    """Uses Claude 3.5 Sonnet to risk-score active marketplace supplier profiles."""

    name = "supplier_sourcing_agent"

    def __init__(self, anthropic_client: AnthropicClient) -> None:
        super().__init__()
        self._claude = anthropic_client

    async def _execute(self, state: PipelineState) -> PipelineState:
        candidates: list[SupplierProfile] = state.get("supplier_candidates", [])
        risk_scores: list[RiskScoreMatrix] = []
        any_approved = False

        for supplier in candidates:
            response_text = await self._claude.complete(
                system_prompt="You are a rigorous supplier risk-scoring analyst.",
                user_prompt=_RISK_SCORING_PROMPT.format(supplier_json=supplier.model_dump_json()),
            )
            try:
                parsed = json.loads(response_text)
                score = RiskScoreMatrix(supplier_id=supplier.supplier_id, **parsed)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                self._log.warning(
                    "supplier_sourcing.parse_failed",
                    supplier_id=supplier.supplier_id,
                    error=str(exc),
                )
                continue

            risk_scores.append(score)
            if score.overall_risk_score < REJECT_THRESHOLD and score.recommendation == "approve":
                any_approved = True

        return {"risk_scores": risk_scores, "supplier_approved": any_approved}
