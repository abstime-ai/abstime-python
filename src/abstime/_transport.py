from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from ._errors import APIConnectionError, InternalError
from ._shared import USER_AGENT, raise_for_http_error


def _build_headers(api_key: str, user_agent: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": user_agent,
    }


def _parse_success_response(response: httpx.Response) -> Tuple[Dict[str, Any], Optional[str]]:
    request_id = response.headers.get("X-Request-Id")
    if not response.content:
        return {}, request_id
    try:
        payload = response.json()
    except ValueError as exc:
        raise InternalError(
            "Invalid JSON response from server.",
            status_code=response.status_code,
            request_id=request_id,
        ) from exc
    if not isinstance(payload, dict):
        raise InternalError(
            "Expected an object response from server.",
            status_code=response.status_code,
            request_id=request_id,
        )
    return payload, request_id


class SyncTransport:
    def __init__(self, *, timeout: int, client: Optional[httpx.Client] = None) -> None:
        self.timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def post_json(
        self,
        *,
        url: str,
        api_key: str,
        body: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        try:
            response = self._client.post(
                url,
                headers=_build_headers(api_key, USER_AGENT),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise APIConnectionError(str(exc)) from exc
        if response.is_error:
            raise_for_http_error(
                raw=response.content,
                status_code=response.status_code,
                request_id=response.headers.get("X-Request-Id"),
            )
        return _parse_success_response(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class AsyncTransport:
    def __init__(self, *, timeout: int, client: Optional[httpx.AsyncClient] = None) -> None:
        self.timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def post_json(
        self,
        *,
        url: str,
        api_key: str,
        body: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        try:
            response = await self._client.post(
                url,
                headers=_build_headers(api_key, USER_AGENT),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise APIConnectionError(str(exc)) from exc
        if response.is_error:
            raise_for_http_error(
                raw=response.content,
                status_code=response.status_code,
                request_id=response.headers.get("X-Request-Id"),
            )
        return _parse_success_response(response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
