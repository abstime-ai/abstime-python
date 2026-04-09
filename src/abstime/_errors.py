from __future__ import annotations

from typing import Any, Dict, Optional


class AbsTimeError(Exception):
    """Base error for the AbsTime library."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        code: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.code = code
        self.raw = raw


class APIConnectionError(AbsTimeError):
    """Network or connection error."""


class InputError(AbsTimeError):
    """Invalid request input."""


class AuthenticationError(AbsTimeError):
    """Authentication or API key error."""


class PermissionDeniedError(AbsTimeError):
    """Permission or plan restriction error."""


class RateLimitError(AbsTimeError):
    """Rate limit or quota error."""


class InternalError(AbsTimeError):
    """Server-side or protocol-level internal error."""


class FieldAccessError(AbsTimeError):
    """A field was accessed in a resolution state where it is not available."""
