from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.catalysts.premarket_engine import _classification, evaluate_premarket_catalysts
from src.scanner.nasdaq100_scanner import _rank_candidates
from src.scoring.scanner_score import score_candidate


class PremarketCatalystEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)
        self.headline = "Company beats estimates and raises full-year guidance"

    def test_single_recognized_source_is_not_confirmed(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [{"title": self.headline, "source": "Reuters", "published": "2026-08-31T12:00:00Z"}],
            market_context={"premarket_change": 5, "rvol_10d": 2},
            now=self.now,
        )
        self.assertFalse(result["confirmed_catalyst"])
        self.assertEqual(result["catalyst_ranking_credit"], 0)
        self.assertEqual(result["validation_state"], "supported_not_confirmed")

    def test_authoritative_source_confirms_positive_catalyst(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [{"title": self.headline, "source": "Company release", "url": "https://www.sec.gov/filing", "published": "2026-08-31T12:00:00Z"}],
            market_context={"premarket_change": 5, "rvol_10d": 2},
            now=self.now,
        )
        self.assertTrue(result["confirmed_catalyst"])
        self.assertGreater(result["catalyst_ranking_credit"], 0)
        self.assertEqual(sum(result["catalyst_score_breakdown"].values()), result["catalyst_score"])

    def test_two_independent_recognized_sources_confirm(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [
                {"title": self.headline, "source": "Reuters", "published": "2026-08-31T12:00:00Z"},
                {"title": self.headline, "source": "Bloomberg", "published": "2026-08-31T12:05:00Z"},
            ],
            now=self.now,
        )
        self.assertTrue(result["confirmed_catalyst"])
        self.assertEqual(result["validation_state"], "confirmed_corroborated")

    def test_different_event_types_do_not_cross_confirm(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [
                {"title": self.headline, "source": "Reuters", "published": "2026-08-31T12:00:00Z"},
                {"title": "Company launches a new product", "source": "Bloomberg", "published": "2026-08-31T12:05:00Z"},
            ],
            now=self.now,
        )
        self.assertFalse(result["confirmed_catalyst"])
        self.assertEqual(result["catalyst_ranking_credit"], 0)

    def test_negative_event_gets_no_long_ranking_credit(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [{"title": "Company misses estimates and cuts guidance", "url": "https://sec.gov/filing", "published": "2026-08-31T12:00:00Z"}],
            now=self.now,
        )
        self.assertTrue(result["confirmed_catalyst"])
        self.assertEqual(result["direction"], "negative")
        self.assertEqual(result["catalyst_ranking_credit"], 0)

    def test_old_authoritative_event_is_not_recent(self) -> None:
        result = evaluate_premarket_catalysts(
            "NVDA",
            [{"title": self.headline, "url": "https://sec.gov/filing", "published": "2026-08-01T12:00:00Z"}],
            now=self.now,
        )
        self.assertFalse(result["confirmed_catalyst"])
        self.assertEqual(result["catalyst_ranking_credit"], 0)
        self.assertIn("stale_or_undated_catalyst_gets_no_recent_catalyst_credit", result["validation_reasons"])

    def test_score_boundaries(self) -> None:
        expected = {
            0: "NOISE", 39.99: "NOISE", 40: "SECONDARY", 59.99: "SECONDARY",
            60: "MATERIAL_CATALYST", 74.99: "MATERIAL_CATALYST",
            75: "STRONG_CATALYST", 89.99: "STRONG_CATALYST", 90: "EXTREME_EVENT", 100: "EXTREME_EVENT",
        }
        for score, label in expected.items():
            self.assertEqual(_classification(score), label)

    def test_unvalidated_headlines_do_not_raise_scanner_catalyst_component(self) -> None:
        scored = score_candidate(
            {
                "news_count": 3,
                "earnings_nearby": True,
                "has_recent_catalyst": False,
                "missing_fields": [],
                "warnings": [],
            }
        )
        self.assertEqual(scored["score_breakdown"]["catalyst"], 0)

    def test_stale_provenance_enforces_score_reduction(self) -> None:
        candidate = {
            "price": 100,
            "change_percent": 5,
            "volume": 1_000_000,
            "rvol_10d": 2,
            "vwap": 99,
            "technical_rating": "STRONG_BUY",
            "rsi": 55,
            "has_recent_catalyst": True,
            "catalyst_ranking_credit": 90,
            "missing_fields": [],
            "warnings": [],
        }
        fresh = score_candidate(candidate)
        candidate["data_provenance"] = {
            "price": {"field": "price", "quality_state": "stale"}
        }
        stale = score_candidate(candidate)
        self.assertLess(stale["total_score"], fresh["total_score"])
        self.assertLessEqual(stale["total_score"], 75)
        self.assertTrue(any("procedencia/frescura" in warning for warning in stale["warnings"]))

    def test_ranking_is_deterministic_for_ties(self) -> None:
        a = [{"ticker": "MSFT", "total_score": 80}, {"ticker": "AAPL", "total_score": 80}]
        b = list(reversed(a))
        self.assertEqual([x["ticker"] for x in _rank_candidates(a)], ["AAPL", "MSFT"])
        self.assertEqual(_rank_candidates(a), _rank_candidates(b))


if __name__ == "__main__":
    unittest.main()
