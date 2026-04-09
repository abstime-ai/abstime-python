import unittest

from abstime import FieldAccessError, InternalError
from abstime._models import Resolution


class ResolutionTests(unittest.TestCase):
    def test_resolved_resolution(self) -> None:
        resolution = Resolution.from_dict(
            {
                "status": "resolved",
                "time": "2026-04-07T22:00:00Z",
                "view": "Apr 7, 2026 3 PM",
                "confidence": "C0",
                "context": {
                    "text": "next Tuesday at 3pm",
                    "ref_time": "2026-04-01T17:30:00Z",
                    "ref_timezone": "America/Los_Angeles",
                },
            },
            request_id="req_123",
        )
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.time, "2026-04-07T22:00:00Z")
        self.assertEqual(resolution.confidence, "C0")
        self.assertEqual(resolution.context.ref_timezone, "America/Los_Angeles")
        self.assertIsNone(resolution.advanced)

    def test_resolved_no_result_hides_time_and_view(self) -> None:
        resolution = Resolution.from_dict(
            {
                "status": "resolved_no_result",
                "confidence": "C1",
                "context": {
                    "text": "January Christmas",
                    "ref_time": "2026-04-01T17:30:00Z",
                    "ref_timezone": "UTC",
                },
            },
            request_id="req_456",
        )
        self.assertEqual(resolution.status, "resolved_no_result")
        self.assertEqual(resolution.confidence, "C1")
        with self.assertRaises(FieldAccessError):
            _ = resolution.time
        with self.assertRaises(FieldAccessError):
            _ = resolution.view

    def test_gated_hides_confidence(self) -> None:
        resolution = Resolution.from_dict(
            {
                "status": "gated",
                "context": {
                    "text": "tomorrow after my next call",
                    "ref_time": "2026-04-01T17:30:00Z",
                    "ref_timezone": "UTC",
                },
                "advanced": {},
            },
            request_id="req_789",
        )
        self.assertEqual(resolution.status, "gated")
        self.assertEqual(resolution.advanced, {})
        with self.assertRaises(FieldAccessError):
            _ = resolution.confidence

    def test_resolved_preserves_request_id_and_advanced(self) -> None:
        resolution = Resolution.from_dict(
            {
                "status": "resolved",
                "time": "2026-04-07T22:00:00Z",
                "view": "Apr 7, 2026 3 PM",
                "confidence": "C0",
                "advanced": {},
                "context": {
                    "text": "next Tuesday at 3pm",
                    "ref_time": "2026-04-01T17:30:00Z",
                    "ref_timezone": "America/Los_Angeles",
                },
            },
            request_id="req_adv",
        )
        self.assertEqual(resolution.request_id, "req_adv")
        self.assertEqual(resolution.advanced, {})

    def test_invalid_resolved_response_raises(self) -> None:
        with self.assertRaises(InternalError):
            Resolution.from_dict(
                {
                    "status": "resolved",
                    "context": {
                        "text": "tomorrow",
                        "ref_time": "2026-04-01T17:30:00Z",
                        "ref_timezone": "UTC",
                    },
                },
                request_id="req_999",
            )

    def test_gated_must_not_include_confidence(self) -> None:
        with self.assertRaises(InternalError):
            Resolution.from_dict(
                {
                    "status": "gated",
                    "confidence": "C2",
                    "context": {
                        "text": "after my meeting",
                        "ref_time": "2026-04-01T17:30:00Z",
                        "ref_timezone": "UTC",
                    },
                },
                request_id="req_bad",
            )
