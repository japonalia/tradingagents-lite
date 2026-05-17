from __future__ import annotations

import json
from pathlib import Path

from src.data_sources.tvremix_client import (
    fetch_financials,
    fetch_news,
    fetch_ohlcv,
    fetch_quote,
    fetch_technicals,
    normalize_tv_symbol,
)

OUTPUT_PATH = Path("reports/generated/tvremix_NVDA_test.json")


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
