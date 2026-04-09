from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, Optional

from ._models import Resolution
from ._shared import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    build_payload,
    parse_resolution,
    require_api_key,
    retry_delay_seconds,
    should_retry_error,
    validate_max_retries,
    validate_retry_delay,
)
from ._transport import AsyncTransport, SyncTransport


class _BaseClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 15,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.api_key = api_key or os.getenv("ABSTIME_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = validate_max_retries(max_retries)
        self.retry_delay = validate_retry_delay(retry_delay)

    def _build_payload(
        self,
        *,
        text: str,
        ref_timezone: str,
        ref_time: Optional[str],
        response_level: str,
    ) -> Dict[str, Any]:
        return build_payload(
            text=text,
            ref_timezone=ref_timezone,
            ref_time=ref_time,
            response_level=response_level,
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"


class AbsTime(_BaseClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 15,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        _transport: Optional[SyncTransport] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._transport = _transport or SyncTransport(timeout=timeout)

    def resolve(
        self,
        *,
        text: str,
        ref_timezone: str,
        ref_time: Optional[str] = None,
        response_level: str = "basic",
    ) -> Resolution:
        payload = self._build_payload(
            text=text,
            ref_timezone=ref_timezone,
            ref_time=ref_time,
            response_level=response_level,
        )
        api_key = require_api_key(self.api_key)
        data, request_id = self._post_with_retry(api_key=api_key, body=payload)
        return parse_resolution(data, request_id=request_id)

    def _post_with_retry(
        self,
        *,
        api_key: str,
        body: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        for attempt in range(self.max_retries + 1):
            try:
                return self._transport.post_json(
                    url=self._url("/v1/resolve"),
                    api_key=api_key,
                    body=body,
                )
            except Exception as exc:
                if not should_retry_error(exc) or attempt >= self.max_retries:
                    raise

                time.sleep(retry_delay_seconds(self.retry_delay, attempt))

        raise RuntimeError("retry loop exited unexpectedly")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "AbsTime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class AsyncAbsTime(_BaseClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 15,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        _transport: Optional[AsyncTransport] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._transport = _transport or AsyncTransport(timeout=timeout)

    async def resolve(
        self,
        *,
        text: str,
        ref_timezone: str,
        ref_time: Optional[str] = None,
        response_level: str = "basic",
    ) -> Resolution:
        payload = self._build_payload(
            text=text,
            ref_timezone=ref_timezone,
            ref_time=ref_time,
            response_level=response_level,
        )
        api_key = require_api_key(self.api_key)
        data, request_id = await self._post_with_retry(api_key=api_key, body=payload)
        return parse_resolution(data, request_id=request_id)

    async def _post_with_retry(
        self,
        *,
        api_key: str,
        body: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        for attempt in range(self.max_retries + 1):
            try:
                return await self._transport.post_json(
                    url=self._url("/v1/resolve"),
                    api_key=api_key,
                    body=body,
                )
            except Exception as exc:
                if not should_retry_error(exc) or attempt >= self.max_retries:
                    raise

                await asyncio.sleep(retry_delay_seconds(self.retry_delay, attempt))

        raise RuntimeError("retry loop exited unexpectedly")

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncAbsTime":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
