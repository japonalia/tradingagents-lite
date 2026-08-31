from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.audit.scanner_audit import build_scanner_audit, universe_hash
from src.catalysts.premarket_engine import evaluate_premarket_catalysts
from src.data_quality.provenance import build_field_provenance


class ScannerAuditAcceptanceTests(unittest.TestCase):
    def test_mixed_quality_fixture_preserves_universe_and_explains_credit(self) -> None:
        now = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)
        universe = ["NASDAQ:NVDA", "NASDAQ:MSFT", "NASDAQ:AAPL", "NASDAQ:AMZN"]
        values = {
            "NVDA": (100, now - timedelta(seconds=30), None),
            "MSFT": (200, now - timedelta(minutes=10), None),
            "AAPL": (300, now, "estimated"),
            "AMZN": (None, None, None),
        }
        candidates = []
        for ticker, (value, observed, hint) in values.items():
            candidates.append(
                {
                    "ticker": ticker,
                    "total_score": 50,
                    "data_provenance": {
                        "price": build_field_provenance(
                            field="price", value=value, source="fixture", observed_at=observed, received_at=now, quality_hint=hint
                        )
                    },
                    "missing_fields": [] if value is not None else ["price"],
                    "warnings": [],
                    "reasons": [],
                }
            )

        unvalidated = evaluate_premarket_catalysts(
            "NVDA",
            [{"title": "Company raises guidance", "source": "Reuters", "published": now.isoformat()}],
            now=now,
        )
        candidates[0].update(
            {
                "catalyst_score": unvalidated["catalyst_score"],
                "catalyst_classification": unvalidated["catalyst_classification"],
                "has_recent_catalyst": unvalidated["confirmed_catalyst"],
                "catalyst_validation_state": unvalidated["validation_state"],
                "reasons": unvalidated["validation_reasons"],
            }
        )
        audit = build_scanner_audit(
            run_id="fixture-run",
            started_at=now,
            completed_at=now,
            universe_symbols=universe,
            universe_source="fixture.yaml",
            candidates=candidates,
        )

        self.assertEqual(audit["universe"]["symbols"], universe)
        self.assertEqual(audit["universe"]["sha256"], universe_hash(universe))
        states = {row["ticker"]: row["quality_states"] for row in audit["candidates"]}
        self.assertEqual(states["NVDA"], ["live"])
        self.assertEqual(states["MSFT"], ["delayed"])
        self.assertEqual(states["AAPL"], ["estimated"])
        self.assertEqual(states["AMZN"], ["unavailable"])
        self.assertFalse(audit["candidates"][0]["confirmed_catalyst"])
        self.assertIn("unvalidated_catalyst_gets_no_confirmed_ranking_credit", audit["candidates"][0]["ranking_reasons"])


if __name__ == "__main__":
    unittest.main()
