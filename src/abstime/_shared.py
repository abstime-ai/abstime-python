from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Tuple, Type

from ._errors import (
    AbsTimeError,
    APIConnectionError,
    AuthenticationError,
    InputError,
    InternalError,
    PermissionDeniedError,
    RateLimitError,
)
from ._models import Resolution

VALID_RESPONSE_LEVELS = {"basic", "advanced"}
DEFAULT_BASE_URL = "https://api.abstime.ai"
USER_AGENT = "abstime-python/0.1.0"
DEFAULT_MAX_RETRIES = 1
DEFAULT_RETRY_DELAY = 0.25
MAX_TEXT_LENGTH = 512


def utc_now_rfc3339() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def build_payload(
    *,
    text: str,
    ref_timezone: str,
    ref_time: Optional[str],
    response_level: str,
) -> Dict[str, Any]:
    if not text or not isinstance(text, str):
        raise InputError("text is required")
    if len(text) > MAX_TEXT_LENGTH:
        raise InputError(f"text must be at most {MAX_TEXT_LENGTH} characters")
    if not ref_timezone or not isinstance(ref_timezone, str):
        raise InputError("ref_timezone is required")
    if response_level not in VALID_RESPONSE_LEVELS:
        raise InputError("response_level must be 'basic' or 'advanced'")

    fixed_ref_time = ref_time if ref_time is not None else utc_now_rfc3339()
    if not isinstance(fixed_ref_time, str) or not fixed_ref_time:
        raise InputError("ref_time must be a non-empty RFC3339 UTC string")
    if not is_valid_rfc3339_utc(fixed_ref_time):
        raise InputError("ref_time must be a valid RFC3339 UTC string")

    payload: Dict[str, Any] = {
        "text": text,
        "ref_time": fixed_ref_time,
        "ref_timezone": ref_timezone,
        "response_level": response_level,
    }
    return payload


def parse_resolution(data: Mapping[str, Any], request_id: Optional[str]) -> Resolution:
    return Resolution.from_dict(data, request_id=request_id)


def parse_error(raw: bytes) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    if not raw:
        return "Request failed.", None, None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError):
        return "Request failed.", None, None

    err = data.get("error") or {}
    message = err.get("message") or "Request failed."
    code = err.get("code")
    return message, code, data


def map_error_class(code: Optional[str], status_code: Optional[int]) -> Type[AbsTimeError]:
    if code == "INVALID_INPUT" or status_code == 400:
        return InputError
    if code == "UNAUTHORIZED" or status_code == 401:
        return AuthenticationError
    if code == "FORBIDDEN" or status_code == 403:
        return PermissionDeniedError
    if code == "RATE_LIMITED" or status_code == 429:
        return RateLimitError
    if code == "INTERNAL_ERROR" or (status_code is not None and status_code >= 500):
        return InternalError
    return AbsTimeError


def raise_for_http_error(
    *,
    raw: bytes,
    status_code: int,
    request_id: Optional[str],
) -> None:
    message, code, raw_error = parse_error(raw)
    error_cls = map_error_class(code, status_code)
    raise error_cls(
        message,
        status_code=status_code,
        request_id=request_id,
        code=code,
        raw=raw_error,
    )


def require_api_key(api_key: Optional[str]) -> str:
    if not api_key:
        raise AuthenticationError("Missing API key.")
    return api_key


def is_valid_rfc3339_utc(value: str) -> bool:
    if value.endswith("Z"):
        candidate = value[:-1] + "+00:00"
    else:
        candidate = value

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False

    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def validate_max_retries(value: int) -> int:
    if not isinstance(value, int) or value < 0:
        raise InputError("max_retries must be a non-negative integer")
    return value


def validate_retry_delay(value: float) -> float:
    if not isinstance(value, (int, float)) or value < 0:
        raise InputError("retry_delay must be a non-negative number")
    return float(value)


def should_retry_error(error: Exception) -> bool:
    if isinstance(error, (APIConnectionError, RateLimitError)):
        return True

    return isinstance(error, InternalError) and error.status_code is not None


def retry_delay_seconds(base_delay: float, retry_index: int) -> float:
    if base_delay <= 0:
        return 0.0

    backoff = base_delay * (2**retry_index)
    jitter = random.uniform(0, max(0.001, base_delay / 4))
    return backoff + jitter


__all__ = [
    "APIConnectionError",
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "MAX_TEXT_LENGTH",
    "USER_AGENT",
    "build_payload",
    "is_valid_rfc3339_utc",
    "parse_resolution",
    "raise_for_http_error",
    "require_api_key",
    "retry_delay_seconds",
    "should_retry_error",
    "validate_max_retries",
    "validate_retry_delay",
]
