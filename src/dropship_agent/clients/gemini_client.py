from __future__ import annotations

from google import genai
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from dropship_agent.clients.base import PermanentClientError, TransientClientError
from dropship_agent.config import Settings
from dropship_agent.logging_utils import get_logger


class GeminiClient:
    """Async wrapper around Gemini 1.5 Flash, used for massive web/trend data parsing."""

    def __init__(self, settings: Settings, *, max_retries: int = 3) -> None:
        api_key = settings.require(settings.google_api_key, "GOOGLE_API_KEY")
        self._client = genai.Client(api_key=api_key)
        self._model = settings.gemini_model
        self._max_retries = max_retries
        self._log = get_logger(self.__class__.__name__)

    async def generate(self, prompt: str, *, temperature: float = 0.3) -> str:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(TransientClientError),
        )
        async def _call() -> str:
            self._log.info("gemini.request.start", model=self._model)
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config={"temperature": temperature},
                )
            except APIError as exc:
                status = getattr(exc, "code", 500)
                if status == 429 or status >= 500:
                    self._log.warning("gemini.request.transient_error", status=status)
                    raise TransientClientError(str(exc)) from exc
                self._log.error("gemini.request.permanent_error", status=status)
                raise PermanentClientError(str(exc)) from exc

            text = response.text or ""
            self._log.info("gemini.request.success", output_chars=len(text))
            return text

        return await _call()
