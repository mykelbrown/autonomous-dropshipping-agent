from __future__ import annotations

from anthropic import APIStatusError, APITimeoutError, AsyncAnthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from dropship_agent.clients.base import PermanentClientError, TransientClientError
from dropship_agent.config import Settings
from dropship_agent.logging_utils import get_logger


class AnthropicClient:
    """Async wrapper around Claude 3.5 Sonnet, used as the core reasoning engine."""

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        api_key = settings.require(settings.anthropic_api_key, "ANTHROPIC_API_KEY")
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = settings.anthropic_model
        self._max_retries = max_retries
        self._log = get_logger(self.__class__.__name__)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(TransientClientError),
        )
        async def _call() -> str:
            self._log.info("anthropic.request.start", model=self._model)
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
            except APITimeoutError as exc:
                self._log.warning("anthropic.request.timeout")
                raise TransientClientError("Anthropic API timeout") from exc
            except APIStatusError as exc:
                if exc.status_code == 429 or exc.status_code >= 500:
                    self._log.warning("anthropic.request.transient_error", status=exc.status_code)
                    raise TransientClientError(str(exc)) from exc
                self._log.error("anthropic.request.permanent_error", status=exc.status_code)
                raise PermanentClientError(str(exc)) from exc

            text = "".join(block.text for block in response.content if block.type == "text")
            self._log.info("anthropic.request.success", output_chars=len(text))
            return text

        return await _call()
