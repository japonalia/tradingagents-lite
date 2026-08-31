from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.data_quality.provenance import build_field_provenance


class ProvenanceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)

    def test_states_are_explicit_and_conservative(self) -> None:
        live = build_field_provenance(
            field="price", value=100, source="fixture", observed_at=self.now - timedelta(seconds=30), received_at=self.now
        )
        delayed = build_field_provenance(
            field="price", value=100, source="fixture", observed_at=self.now - timedelta(minutes=10), received_at=self.now
        )
        stale = build_field_provenance(
            field="price", value=100, source="fixture", observed_at=self.now - timedelta(hours=2), received_at=self.now
        )
        estimated = build_field_provenance(
            field="price", value=100, source="fixture", observed_at=self.now, received_at=self.now, quality_hint="estimated"
        )
        missing = build_field_provenance(
            field="price", value=None, source="fixture", observed_at=self.now, received_at=self.now
        )
        unknown = build_field_provenance(
            field="price", value=100, source="fixture", observed_at=None, received_at=self.now
        )

        self.assertEqual(live["quality_state"], "live")
        self.assertEqual(delayed["quality_state"], "delayed")
        self.assertEqual(stale["quality_state"], "stale")
        self.assertEqual(estimated["quality_state"], "estimated")
        self.assertEqual(missing["quality_state"], "unavailable")
        self.assertEqual(unknown["quality_state"], "unknown")
        for record in (delayed, stale, estimated, missing, unknown):
            self.assertFalse(record["is_usable_for_live_claim"])

    def test_explicit_stale_or_estimated_never_becomes_live(self) -> None:
        for hint in ("stale", "estimated"):
            record = build_field_provenance(
                field="vwap", value=50, source="fixture", observed_at=self.now, received_at=self.now, quality_hint=hint
            )
            self.assertEqual(record["quality_state"], hint)
            self.assertFalse(record["is_usable_for_live_claim"])

    def test_future_timestamp_is_not_live(self) -> None:
        record = build_field_provenance(
            field="price",
            value=100,
            source="fixture",
            observed_at=self.now + timedelta(minutes=5),
            received_at=self.now,
        )
        self.assertEqual(record["quality_state"], "unknown")
        self.assertFalse(record["is_usable_for_live_claim"])


if __name__ == "__main__":
    unittest.main()
