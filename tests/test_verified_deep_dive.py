from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from src.data_sources.tvremix_client import fetch_verified_intraday_deep_dive


def frame(base: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Date": "2026-08-31T13:30:00Z", "Open": base, "High": base + 2, "Low": base - 1, "Close": base + 1, "Volume": 100},
            {"Date": "2026-08-31T13:35:00Z", "Open": base + 1, "High": base + 3, "Low": base, "Close": base + 2, "Volume": 200},
        ]
    )


class VerifiedDeepDiveTests(unittest.TestCase):
    @patch("src.data_sources.tvremix_client.fetch_ohlcv")
    def test_qqq_is_loaded_once_and_reused(self, mock_fetch):
        mock_fetch.side_effect = lambda symbol, **kwargs: (frame(200 if symbol == "NASDAQ:QQQ" else 100), [])
        records, warnings, diagnostics = fetch_verified_intraday_deep_dive(
            ["NVDA", "MSFT", "AAPL", "AMZN", "META"],
            as_of=datetime(2026, 8, 31, 13, 42, tzinfo=timezone.utc),
        )
        self.assertFalse(warnings)
        self.assertEqual(diagnostics["qqq_calls"], 1)
        self.assertEqual(diagnostics["symbols_verified"], 5)
        self.assertEqual(mock_fetch.call_count, 6)
        self.assertTrue(all(records[symbol]["relative_strength_alignment"]["quality"] == "timestamp_verified" for symbol in ["NVDA", "MSFT", "AAPL", "AMZN", "META"]))


if __name__ == "__main__":
    unittest.main()
