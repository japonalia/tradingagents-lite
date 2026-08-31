from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.audit.scanner_audit import build_scanner_audit, write_scanner_audit
from src.catalysts.premarket_engine import evaluate_premarket_catalysts
from src.data_quality.provenance import build_field_provenance


OUTPUT_PATH = Path("reports/generated/scanner_contract_fixture_audit.json")


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    universe = ["NASDAQ:NVDA", "NASDAQ:MSFT", "NASDAQ:AAPL", "NASDAQ:AMZN"]
    fixture = {
        "NVDA": (100.0, now - timedelta(seconds=30), None),
        "MSFT": (200.0, now - timedelta(minutes=10), None),
        "AAPL": (300.0, now, "estimated"),
        "AMZN": (None, None, None),
    }
    candidates = []
    for ticker, (value, observed_at, quality_hint) in fixture.items():
        candidates.append(
            {
                "ticker": ticker,
                "total_score": 50.0,
                "has_recent_catalyst": False,
                "catalyst_score": 0.0,
                "catalyst_classification": "NOISE",
                "catalyst_validation_state": "unverified",
                "data_provenance": {
                    "price": build_field_provenance(
                        field="price",
                        value=value,
                        source="automated_acceptance_fixture",
                        observed_at=observed_at,
                        received_at=now,
                        quality_hint=quality_hint,
                    )
                },
                "missing_fields": [] if value is not None else ["price"],
                "warnings": [],
                "reasons": [],
            }
        )

    catalyst = evaluate_premarket_catalysts(
        "NVDA",
        [{"title": "Company raises guidance", "source": "Reuters", "published": now.isoformat()}],
        now=now,
    )
    candidates[0].update(
        {
            "catalyst_score": catalyst["catalyst_score"],
            "catalyst_classification": catalyst["catalyst_classification"],
            "has_recent_catalyst": catalyst["confirmed_catalyst"],
            "catalyst_validation_state": catalyst["validation_state"],
            "reasons": catalyst["validation_reasons"],
        }
    )

    audit = build_scanner_audit(
        run_id="automated-acceptance-fixture",
        started_at=now,
        completed_at=datetime.now(timezone.utc),
        universe_symbols=universe,
        universe_source="automated_acceptance_fixture",
        candidates=candidates,
        global_warnings=[
            "FIXTURE_ONLY: no contiene datos de mercado reales y no debe utilizarse para operar."
        ],
    )
    write_scanner_audit(audit, OUTPUT_PATH)
    print(f"Contract fixture audit written to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
