# AbsTime Python API Library

AbsTime resolves natural language time expressions for AI systems.

Built for agents, assistants, and workflows that need accurate time resolution.

This library provides convenient access to the AbsTime REST API from Python.

## Install

```bash
pip install abstime
```

## Quickstart

```python
import os

from abstime import AbsTime

client = AbsTime(api_key=os.environ["ABSTIME_API_KEY"])

result = client.resolve(
    text="the last Friday of this month at 2 pm",
    ref_time="2026-04-09T17:30:00Z",
    ref_timezone="America/Los_Angeles",
)

print(result.time)
print(result.view)
# 2026-04-24T21:00:00Z
# Apr 24, 2026 2 PM
```

## Output

The core result fields are:

| Field | Meaning | Example | Use |
| --- | --- | --- | --- |
| `time` | Resolved UTC timestamp | `2026-04-24T21:00:00Z` | Store, compare, or pass to downstream systems |
| `view` | Human-readable local time | `Apr 24, 2026 2 PM` | Show the result in user interfaces |
| `confidence` | Resolution confidence signal | `C0` | Guide result presentation and handling |

Understand `confidence`:
- `C0`: a clear resolution; safe to use directly.
- `C1`: less obvious but the most reasonable resolution; still safe to use directly.
- `C2`: sometimes arguable; user confirmation is recommended.

## Input

The core input fields are:

| Field | Meaning | Use | Instead of |
| --- | --- | --- | --- |
| `text` | Natural language time expression | `two days before Christmas` | `Schedule a meeting with Lily two days before Christmas.` |
| `ref_time` | UTC reference time | `2026-04-09T17:30:00Z` | `2026-04-09T10:30:00-07:00` |
| `ref_timezone` | IANA reference timezone | `America/Los_Angeles` | `PST` |

## Handling Errors

When the library is unable to connect to the API, for example due to a network failure or timeout, an `abstime.APIConnectionError` is raised.

When the API returns a non-success status code, a subclass of `abstime.AbsTimeError` is raised.

```python
import abstime

client = abstime.AbsTime()

try:
    result = client.resolve(
        text="the last Friday of this month at 2 pm",
        ref_time="2026-04-09T17:30:00Z",
        ref_timezone="America/Los_Angeles",
    )
except abstime.InputError as exc:
    print(f"Invalid input: {exc}")
except abstime.RateLimitError as exc:
    print(f"Request ID: {exc.request_id}")
except abstime.APIConnectionError:
    print("The API could not be reached.")
```

Error codes are as follows:

| Status Code | Error |
| --- | --- |
| `400` | `InputError` |
| `401` | `AuthenticationError` |
| `403` | `PermissionDeniedError` |
| `429` | `RateLimitError` |
| `>=500` | `InternalError` |
| `N/A` | `APIConnectionError` |

## Request IDs

All successful responses provide a `request_id` from the `X-Request-Id` response header.

```python
print(result.request_id)
```

For failed requests, catch the error and read `exc.request_id`:

```python
import abstime

try:
    client.resolve(
        text="the last Friday of this month at 2 pm",
        ref_time="2026-04-09T17:30:00Z",
        ref_timezone="America/Los_Angeles",
    )
except abstime.AbsTimeError as exc:
    print(exc.request_id)
```

## Retries and Timeouts

The client retries certain transient failures once by default with a short backoff.

Requests time out after 15 seconds by default.

You can configure both when creating the client.

```python
client = abstime.AbsTime(
    timeout=5,
    max_retries=0,
)
```

## Async Usage

Import `AsyncAbsTime` instead of `AbsTime` and use `await` with each call:

```python
import asyncio

from abstime import AsyncAbsTime

client = AsyncAbsTime()


async def main() -> None:
    result = await client.resolve(
        text="the last Friday of this month at 2 pm",
        ref_time="2026-04-09T17:30:00Z",
        ref_timezone="America/Los_Angeles",
    )
    print(result.time)


asyncio.run(main())
```

The synchronous and asynchronous clients are otherwise identical.

## Requirements

- Python 3.9+

## Docs

See [docs.abstime.ai](https://docs.abstime.ai) for the full API contract, response details, and integration guides.
