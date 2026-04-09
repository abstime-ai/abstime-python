import asyncio
import unittest
from unittest.mock import patch

from abstime import (
    AbsTime,
    APIConnectionError,
    AsyncAbsTime,
    AuthenticationError,
    InputError,
    RateLimitError,
)


class _FakeSyncTransport:
    def __init__(self) -> None:
        self.calls = []

    def post_json(self, *, url, api_key, body):
        self.calls.append({"url": url, "api_key": api_key, "body": body})
        return (
            {
                "status": "resolved",
                "time": "2026-04-07T22:00:00Z",
                "view": "Apr 7, 2026 3 PM",
                "confidence": "C0",
                "context": {
                    "text": body["text"],
                    "ref_time": body["ref_time"],
                    "ref_timezone": body["ref_timezone"],
                },
            },
            "req_sync",
        )


class _FakeAsyncTransport:
    def __init__(self) -> None:
        self.calls = []

    async def post_json(self, *, url, api_key, body):
        self.calls.append({"url": url, "api_key": api_key, "body": body})
        return (
            {
                "status": "gated",
                "context": {
                    "text": body["text"],
                    "ref_time": body["ref_time"],
                    "ref_timezone": body["ref_timezone"],
                },
            },
            "req_async",
        )


class ClientTests(unittest.TestCase):
    def test_sync_client_uses_new_route_and_fields(self) -> None:
        transport = _FakeSyncTransport()
        client = AbsTime(api_key="test_key", _transport=transport)

        resolution = client.resolve(
            text="next Tuesday at 3pm",
            ref_time="2026-04-01T17:30:00Z",
            ref_timezone="America/Los_Angeles",
            response_level="advanced",
        )

        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(transport.calls[0]["url"], "https://api.abstime.ai/v1/resolve")
        self.assertEqual(transport.calls[0]["body"]["text"], "next Tuesday at 3pm")
        self.assertEqual(transport.calls[0]["body"]["ref_timezone"], "America/Los_Angeles")
        self.assertEqual(transport.calls[0]["body"]["response_level"], "advanced")
        self.assertEqual(resolution.request_id, "req_sync")

    def test_sync_client_requires_api_key(self) -> None:
        client = AbsTime(api_key=None)
        with self.assertRaises(AuthenticationError):
            client.resolve(text="tomorrow", ref_timezone="UTC")

    def test_sync_client_validates_response_level(self) -> None:
        client = AbsTime(api_key="test_key", _transport=_FakeSyncTransport())
        with self.assertRaises(InputError):
            client.resolve(text="tomorrow", ref_timezone="UTC", response_level="debug")

    def test_sync_client_validates_ref_time_locally(self) -> None:
        client = AbsTime(api_key="test_key", _transport=_FakeSyncTransport())

        with self.assertRaises(InputError):
            client.resolve(
                text="tomorrow",
                ref_timezone="UTC",
                ref_time="2026-04-01T17:30:00+08:00",
            )

    def test_sync_client_validates_text_length_locally(self) -> None:
        client = AbsTime(api_key="test_key", _transport=_FakeSyncTransport())

        with self.assertRaises(InputError):
            client.resolve(text="a" * 513, ref_timezone="UTC")

    def test_sync_client_fills_ref_time_when_omitted(self) -> None:
        transport = _FakeSyncTransport()
        client = AbsTime(api_key="test_key", _transport=transport)

        with patch("abstime._shared.utc_now_rfc3339", return_value="2026-04-01T08:00:00Z"):
            resolution = client.resolve(text="tomorrow", ref_timezone="UTC")

        self.assertEqual(transport.calls[0]["body"]["ref_time"], "2026-04-01T08:00:00Z")
        self.assertEqual(resolution.context.ref_time, "2026-04-01T08:00:00Z")

    def test_sync_client_maps_http_errors(self) -> None:
        class _ErrorTransport:
            def post_json(self, *, url, api_key, body):
                raise RateLimitError("Slow down.", request_id="req_rate")

        client = AbsTime(api_key="test_key", _transport=_ErrorTransport())

        with self.assertRaises(RateLimitError) as ctx:
            client.resolve(text="tomorrow", ref_timezone="UTC")

        self.assertEqual(ctx.exception.request_id, "req_rate")

    def test_sync_client_retries_transient_failures_once_by_default(self) -> None:
        class _FlakyTransport:
            def __init__(self) -> None:
                self.calls = 0

            def post_json(self, *, url, api_key, body):
                self.calls += 1
                if self.calls == 1:
                    raise APIConnectionError("socket hang up")

                return (
                    {
                        "status": "resolved",
                        "time": "2026-04-02T09:00:00Z",
                        "view": "Apr 2, 2026 9 AM",
                        "confidence": "C0",
                        "context": {
                            "text": body["text"],
                            "ref_time": body["ref_time"],
                            "ref_timezone": body["ref_timezone"],
                        },
                    },
                    "req_retry",
                )

        transport = _FlakyTransport()
        client = AbsTime(api_key="test_key", retry_delay=0, _transport=transport)

        resolution = client.resolve(
            text="tomorrow",
            ref_time="2026-04-01T09:00:00Z",
            ref_timezone="UTC",
        )

        self.assertEqual(transport.calls, 2)
        self.assertEqual(resolution.status, "resolved")

    def test_sync_client_stops_after_max_retries(self) -> None:
        class _AlwaysFailTransport:
            def __init__(self) -> None:
                self.calls = 0

            def post_json(self, *, url, api_key, body):
                self.calls += 1
                raise APIConnectionError("network unavailable")

        transport = _AlwaysFailTransport()
        client = AbsTime(
            api_key="test_key",
            max_retries=1,
            retry_delay=0,
            _transport=transport,
        )

        with self.assertRaises(APIConnectionError):
            client.resolve(text="tomorrow", ref_timezone="UTC")

        self.assertEqual(transport.calls, 2)

    def test_async_client_matches_contract(self) -> None:
        async def _run() -> None:
            transport = _FakeAsyncTransport()
            client = AsyncAbsTime(api_key="test_key", _transport=transport)
            resolution = await client.resolve(
                text="tomorrow",
                ref_time="2026-04-01T17:30:00Z",
                ref_timezone="UTC",
            )
            self.assertEqual(resolution.status, "gated")
            self.assertEqual(transport.calls[0]["url"], "https://api.abstime.ai/v1/resolve")
            self.assertEqual(resolution.request_id, "req_async")

        asyncio.run(_run())
