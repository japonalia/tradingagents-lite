from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data_sources.tvremix_client import fetch_quotes_batch

OUTPUT_PATH = Path("reports/generated/tvremix_quotes_batch_test.json")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _symbol_fields(payload: dict[str, dict[str, Any]], symbols: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for symbol in symbols:
        short = symbol.split(":", 1)[-1].upper()
        data = payload.get(symbol) or payload.get(short) or {}
        out[symbol] = sorted(data.keys()) if isinstance(data, dict) else []
    return out


def main() -> int:
    symbols = ["NASDAQ:NVDA", "NASDAQ:MSFT", "NASDAQ:AAPL"]
    try:
        quotes_map, warnings = fetch_quotes_batch(symbols)
    except Exception as exc:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "requested_symbols": symbols,
            "status": "error",
            "error": str(exc),
        }
        OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"error: {exc}")
        print(f"Salida guardada en: {OUTPUT_PATH}")
        return 1

    sorted_keys = sorted(quotes_map.keys())
    first_keys = sorted_keys[:10]

    report = {
        "requested_symbols": symbols,
        "warnings": warnings,
        "top_level_keys": sorted_keys,
        "data_type": type(quotes_map).__name__,
        "first_symbols_found": first_keys,
        "fields_per_symbol": _symbol_fields(quotes_map, symbols),
        "sample_payload": {
            key: _sanitize(quotes_map[key]) for key in first_keys[:3]
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("top-level keys:", report["top_level_keys"])
    print("data type:", report["data_type"])
    print("primeros símbolos encontrados:", report["first_symbols_found"])
    print("campos por símbolo:")
    for symbol, fields in report["fields_per_symbol"].items():
        print(f"- {symbol}: {fields}")
    print(f"Salida guardada en: {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
