from __future__ import annotations

import json
from pathlib import Path

from src.data_sources.tvremix_client import (
    fetch_tvremix_data,
    fetch_financials,
    fetch_news,
    fetch_ohlcv,
    fetch_quote,
    fetch_technicals,
    normalize_tv_symbol,
)

OUTPUT_PATH = Path("reports/generated/tvremix_NVDA_test.json")
PARSED_OUTPUT_PATH = Path("reports/generated/tvremix_NVDA_test_parsed.json")


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)
    return obj


def main() -> int:
    symbol = normalize_tv_symbol("NVDA")
    output = {"symbol": symbol, "tests": {}}

    tasks = [
        ("get_quote", lambda: fetch_quote(symbol)),
        ("get_technicals", lambda: fetch_technicals(symbol)),
        ("get_financials", lambda: fetch_financials(symbol)),
        ("get_news", lambda: fetch_news(symbol, limit=5)),
        ("get_ohlcv", lambda: fetch_ohlcv(symbol, interval="1D", count=50)),
    ]

    for name, fn in tasks:
        try:
            payload, warnings = fn()
            if name == "get_ohlcv":
                payload = payload.head(3).to_dict(orient="records")
            output["tests"][name] = {
                "status": "ok",
                "warnings": warnings,
                "payload_preview": _sanitize(payload),
            }
        except Exception as exc:
            output["tests"][name] = {"status": "error", "error": str(exc)}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salida guardada en: {OUTPUT_PATH}")

    parsed_output: dict[str, object] = {"symbol": symbol}
    try:
        parsed = fetch_tvremix_data("NVDA")
        parsed_output = {
            "symbol": parsed.symbol,
            "source": parsed.source,
            "missing_fields": parsed.missing_fields,
            "warnings": parsed.warnings,
            "history_rows": int(len(parsed.history)),
            "market_data_summary": _sanitize(parsed.market_data),
        }
    except Exception as exc:
        parsed_output = {"symbol": symbol, "status": "error", "error": str(exc)}

    PARSED_OUTPUT_PATH.write_text(
        json.dumps(parsed_output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Salida parseada guardada en: {PARSED_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
