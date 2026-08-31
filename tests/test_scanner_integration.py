from __future__ import annotations

import unittest
from unittest.mock import patch

from src.scanner.nasdaq100_scanner import scan_nasdaq100


class ScannerIntegrationTests(unittest.TestCase):
    @patch("src.scanner.nasdaq100_scanner.fetch_multi_timeframe_technicals_batch")
    @patch("src.scanner.nasdaq100_scanner.fetch_news_for_symbols")
    @patch("src.scanner.nasdaq100_scanner.fetch_quotes_batch")
    @patch("src.scanner.nasdaq100_scanner.load_nasdaq100_symbols")
    def test_universe_catalyst_scope_and_audit_are_end_to_end(
        self,
        mock_load,
        mock_quotes,
        mock_news,
        mock_technicals,
    ) -> None:
        universe = ["NASDAQ:NVDA", "NASDAQ:MSFT", "NASDAQ:AAPL", "NASDAQ:AMZN"]
        mock_load.return_value = universe

        def quotes_side_effect(symbols):
            if symbols == ["QQQ"]:
                return {"QQQ": {"change_percent": 0.5, "timestamp": "2026-08-31T13:00:00Z"}}, []
            return {
                symbol: {
                    "price": 100 + index,
                    "change_percent": 2 + index,
                    "volume": 1_000_000,
                    "timestamp": "2026-08-31T13:00:00Z",
                }
                for index, symbol in enumerate(symbols)
            }, []

        mock_quotes.side_effect = quotes_side_effect
        mock_news.return_value = (
            {
                symbol: [
                    {
                        "title": "Company beats estimates and raises guidance",
                        "url": "https://www.sec.gov/filing",
                        "published": "2026-08-31T12:00:00Z",
                    }
                ]
                for symbol in universe
            },
            [],
        )
        mock_technicals.return_value = (
            {
                symbol: {"technical_rating": "BUY", "rsi": 55, "timestamp": "2026-08-31T00:00:00Z"}
                for symbol in universe
            },
            [],
        )

        result = scan_nasdaq100(
            limit=4,
            technical_top_n=4,
            catalyst_top_n=1,
            catalyst_scope="universe",
            skip_earnings=True,
            use_intraday=False,
            use_ohlcv_levels=False,
        )

        requested_symbols = mock_news.call_args.args[0]
        self.assertEqual(requested_symbols, universe)
        self.assertEqual(result["catalysts_queried"], 4)
        self.assertEqual(result["audit"]["universe"]["symbols"], universe)
        self.assertEqual(result["audit"]["candidate_count"], 4)
        self.assertTrue(all(candidate["has_recent_catalyst"] for candidate in result["candidates"]))
        self.assertTrue(all(candidate["catalyst_score"] > 0 for candidate in result["candidates"]))


if __name__ == "__main__":
    unittest.main()
