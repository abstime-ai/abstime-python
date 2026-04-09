from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from ._errors import FieldAccessError, InternalError

VALID_STATUSES = {"resolved", "resolved_no_result", "gated"}


@dataclass(frozen=True)
class Context:
    text: str
    ref_time: str
    ref_timezone: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Context":
        try:
            text = str(data["text"])
            ref_time = str(data["ref_time"])
            ref_timezone = str(data["ref_timezone"])
        except KeyError as exc:
            raise InternalError(f"Missing required context field: {exc.args[0]}") from exc
        return cls(text=text, ref_time=ref_time, ref_timezone=ref_timezone)

    def to_dict(self) -> Dict[str, str]:
        return {
            "text": self.text,
            "ref_time": self.ref_time,
            "ref_timezone": self.ref_timezone,
        }


class Resolution:
    """Outcome of a resolve call.

    `status` is the primary routing field:

    - `resolved`: AbsTime produced a canonical machine time.
    - `resolved_no_result`: AbsTime completed resolution and determined that no correct
      time object exists.
    - `gated`: AbsTime stopped at the configured boundary before producing a final result.
    """

    __slots__ = ("status", "context", "request_id", "advanced", "_fields")

    def __init__(
        self,
        *,
        status: str,
        context: Context,
        request_id: Optional[str],
        advanced: Optional[Dict[str, Any]],
        fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        if status not in VALID_STATUSES:
            raise InternalError(f"Invalid resolution status: {status}")
        self.status = status
        self.context = context
        self.request_id = request_id
        self.advanced = advanced
        self._fields = fields or {}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], request_id: Optional[str]) -> "Resolution":
        try:
            status = str(data["status"])
        except KeyError as exc:
            raise InternalError(
                "Missing required response field: status",
                request_id=request_id,
            ) from exc

        if status not in VALID_STATUSES:
            raise InternalError(
                f"Invalid resolution status: {status}",
                request_id=request_id,
            )

        context_raw = data.get("context")
        if not isinstance(context_raw, Mapping):
            raise InternalError(
                "Missing required response field: context",
                request_id=request_id,
                raw=dict(data),
            )
        context = Context.from_dict(context_raw)

        advanced_raw = data.get("advanced")
        if advanced_raw is not None and not isinstance(advanced_raw, Mapping):
            raise InternalError(
                "advanced must be an object when present",
                request_id=request_id,
                raw=dict(data),
            )
        advanced = dict(advanced_raw) if isinstance(advanced_raw, Mapping) else None

        fields: Dict[str, Any] = {}
        for key in ("time", "view", "confidence"):
            if key in data:
                fields[key] = data[key]

        if status == "resolved":
            for key in ("time", "confidence"):
                if key not in fields:
                    raise InternalError(
                        f"Missing required response field for resolved status: {key}",
                        request_id=request_id,
                        raw=dict(data),
                    )
        elif status == "resolved_no_result":
            if "time" in fields or "view" in fields:
                raise InternalError(
                    "resolved_no_result must not include time or view",
                    request_id=request_id,
                    raw=dict(data),
                )
            if "confidence" not in fields:
                raise InternalError(
                    "Missing required response field for resolved_no_result status: confidence",
                    request_id=request_id,
                    raw=dict(data),
                )
        elif status == "gated":
            for key in ("time", "view", "confidence"):
                if key in fields:
                    raise InternalError(
                        f"gated must not include {key}",
                        request_id=request_id,
                        raw=dict(data),
                    )

        return cls(
            status=status,
            context=context,
            request_id=request_id,
            advanced=advanced,
            fields=fields,
        )

    @property
    def time(self) -> str:
        """Canonical machine time for storage and downstream logic."""
        if "time" not in self._fields:
            raise FieldAccessError(f"time is not available when status={self.status!r}")
        return str(self._fields["time"])

    @property
    def view(self) -> Any:
        """Recommended human-facing display projection of the resolved time."""
        if "view" not in self._fields:
            raise FieldAccessError(f"view is not available when status={self.status!r}")
        return self._fields["view"]

    @property
    def confidence(self) -> str:
        """Recommended action level for the current resolution.

        - `C0`: Safe to adopt directly with no end-user prompt.
        - `C1`: Usually safe to adopt directly; highly audited environments may choose
          to explain why.
        - `C2`: Do not adopt silently; show a visible verification cue to the end user.
        """
        if "confidence" not in self._fields:
            raise FieldAccessError(f"confidence is not available when status={self.status!r}")
        return str(self._fields["confidence"])

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "status": self.status,
            "context": self.context.to_dict(),
        }
        data.update(self._fields)
        if self.advanced is not None:
            data["advanced"] = self.advanced
        return data

    def __repr__(self) -> str:
        bits = [f"status={self.status!r}"]
        if "time" in self._fields:
            bits.append(f"time={self._fields['time']!r}")
        if "confidence" in self._fields:
            bits.append(f"confidence={self._fields['confidence']!r}")
        return f"Resolution({', '.join(bits)})"
