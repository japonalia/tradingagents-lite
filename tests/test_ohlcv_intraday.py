from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.indicators.ohlcv_intraday import derive_intraday_metrics, relative_strength_from_aligned_bars


def bar(ts, o, h, l, c, v=100):
    return {"timestamp": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}


class OhlcvIntradayTests(unittest.TestCase):
    def setUp(self):
        self.as_of = datetime(2026, 8, 31, 13, 42, tzinfo=timezone.utc)
        self.rows = [
            bar("2026-08-28T13:30:00Z", 90, 91, 89, 90, 999),
            bar("2026-08-31T13:30:00Z", 100, 102, 99, 101, 100),
            bar("2026-08-31T13:35:00Z", 101, 103, 100, 102, 200),
            bar("2026-08-31T13:40:00Z", 102, 110, 98, 109, 500),
        ]

    def test_excludes_previous_session_and_incomplete_bar(self):
        result = derive_intraday_metrics(self.rows, as_of=self.as_of, interval="5m")
        self.assertEqual(result["bars_used"], 2)
        self.assertEqual(result["discarded_incomplete_bars"], 1)
        self.assertEqual(result["last_completed_bar_close"], 102)
        self.assertEqual(result["session_open"], 100)
        self.assertEqual(result["session_high"], 103)
        self.assertEqual(result["session_low"], 99)
        self.assertEqual(result["session_volume"], 300)
        self.assertEqual(result["quality"], "delayed")

    def test_orb_and_blocked_metrics_are_explicit(self):
        result = derive_intraday_metrics(self.rows, as_of=self.as_of, interval="5m")
        self.assertEqual((result["orb_5_high"], result["orb_5_low"]), (102, 99))
        self.assertEqual((result["orb_15_high"], result["orb_15_low"]), (None, None))
        self.assertIsNone(result["vwap"])
        self.assertEqual(result["ohlcv_vwap_proxy_quality"], "estimated")
        self.assertEqual(result["ohlcv_vwap_proxy_ranking_credit"], 0)
        self.assertIsNone(result["rvol"])

    def test_relative_strength_requires_common_completed_bars(self):
        qqq = [
            bar("2026-08-31T13:30:00Z", 200, 202, 199, 201),
            bar("2026-08-31T13:35:00Z", 201, 202, 200, 202),
        ]
        result = relative_strength_from_aligned_bars(self.rows, qqq, as_of=self.as_of)
        self.assertEqual(result["aligned_bars"], 2)
        self.assertEqual(result["quality"], "timestamp_verified")

    def test_unaligned_qqq_blocks_relative_strength(self):
        qqq = [bar("2026-08-31T14:00:00Z", 200, 201, 199, 200)]
        result = relative_strength_from_aligned_bars(self.rows, qqq, as_of=self.as_of)
        self.assertIsNone(result["relative_strength_vs_qqq"])
        self.assertEqual(result["reason"], "qqq_alignment_unverified")


if __name__ == "__main__":
    unittest.main()
