from __future__ import annotations

from abc import ABC, abstractmethod

from tenacity import retry, stop_after_attempt, wait_exponential

from dropship_agent.logging_utils import get_logger
from dropship_agent.models.graph_state import PipelineState


class BaseAgent(ABC):
    """Common agent lifecycle: reasoning-step logging + self-healing retries.

    Subclasses implement `_execute`, which reads/writes `PipelineState`. `run` wraps
    it with structured logging (agent name, reasoning step, elapsed time) and retries
    on any exception so a single flaky LLM/API call doesn't kill the whole graph run.
    """

    name: str = "base_agent"
    max_retries: int = 3

    def __init__(self) -> None:
        self._log = get_logger(self.name)

    @abstractmethod
    async def _execute(self, state: PipelineState) -> PipelineState:
        """Perform the agent's work and return the state updates to merge."""

    async def run(self, state: PipelineState) -> PipelineState:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
        )
        async def _attempt() -> PipelineState:
            self._log.info("agent.step.start", agent=self.name)
            try:
                result = await self._execute(state)
            except Exception as exc:
                self._log.warning("agent.step.retrying", agent=self.name, error=str(exc))
                raise
            self._log.info("agent.step.success", agent=self.name, keys=list(result.keys()))
            return result

        try:
            return await _attempt()
        except Exception as exc:
            self._log.error("agent.step.failed", agent=self.name, error=str(exc))
            return {"errors": [f"{self.name}: {exc}"]}
