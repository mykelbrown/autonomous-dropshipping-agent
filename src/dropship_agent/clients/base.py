from __future__ import annotations

from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dropship_agent.logging_utils import get_logger


class ClientError(Exception):
    """Base error for all external client failures."""


class TransientClientError(ClientError):
    """Retryable error: timeouts, 429s, 5xx responses."""


class PermanentClientError(ClientError):
    """Non-retryable error: 4xx auth/validation failures, malformed config."""


def _raise_for_status(response: httpx.Response) -> None:
    status, url, body = response.status_code, response.request.url, response.text[:500]
    if status == 429 or status >= 500:
        raise TransientClientError(f"Transient HTTP {status} from {url}: {body}")
    if status >= 400:
        raise PermanentClientError(f"HTTP {status} from {url}: {body}")


class BaseAsyncClient:
    """Shared async HTTP client behavior: retry/backoff, timeouts, structured logging.

    Subclasses (Anthropic, Gemini, Amazon, eBay, Shopify, scraping proxies) implement
    thin domain-specific methods on top of `_request`, inheriting self-healing retries
    and consistent status/latency logging for free.
    """

    def __init__(self, base_url: str, *, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.base_url = base_url
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._log = get_logger(self.__class__.__name__)

    async def __aenter__(self) -> BaseAsyncClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        """Type-narrowing helper: httpx's `.json()` returns Any."""
        return cast(dict[str, Any], response.json())

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(TransientClientError),
        )
        async def _do_request() -> httpx.Response:
            self._log.info(
                "client.request.start", method=method, path=path, base_url=self.base_url
            )
            try:
                response = await self._client.request(
                    method, path, params=params, json=json, data=data, headers=headers
                )
            except httpx.TimeoutException as exc:
                self._log.warning("client.request.timeout", method=method, path=path)
                raise TransientClientError(f"Timeout calling {path}") from exc
            except httpx.TransportError as exc:
                self._log.warning(
                    "client.request.transport_error", method=method, path=path, error=str(exc)
                )
                raise TransientClientError(f"Transport error calling {path}: {exc}") from exc

            _raise_for_status(response)
            self._log.info(
                "client.request.success",
                method=method,
                path=path,
                status_code=response.status_code,
                latency_ms=response.elapsed.total_seconds() * 1000 if response.elapsed else None,
            )
            return response

        try:
            return await _do_request()
        except PermanentClientError as exc:
            self._log.error(
                "client.request.permanent_failure", method=method, path=path, error=str(exc)
            )
            raise
        except TransientClientError as exc:
            self._log.error(
                "client.request.exhausted_retries", method=method, path=path, error=str(exc)
            )
            raise
