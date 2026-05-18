from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data_sources.tvremix_client import call_tool, parse_mcp_text_payload

OUTPUT_PATH = Path("reports/generated/tvremix_multitimeframe_batch_test.json")


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


def _collect_numeric_fields(value: Any, prefix: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            found |= _collect_numeric_fields(v, path)
    elif isinstance(value, list):
        for idx, item in enumerate(value[:20]):
            found |= _collect_numeric_fields(item, f"{prefix}[{idx}]")
    elif isinstance(value, (int, float)):
        found.add(prefix)
    return found


def _first_symbol_sample(data: Any, preferred: list[str]) -> tuple[str | None, Any]:
    if isinstance(data, dict):
        for symbol in preferred:
            if symbol in data:
                return symbol, data[symbol]
            short = symbol.split(":", 1)[-1]
            if short in data:
                return short, data[short]
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                return str(k), v
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return str(item.get("symbol") or item.get("ticker") or "item"), item
    return None, None


def main() -> int:
    symbols = ["NASDAQ:NVDA", "NASDAQ:MSFT", "NASDAQ:AAPL", "NASDAQ:AVGO", "NASDAQ:AMD"]
    try:
        raw = call_tool("analyze_multi_timeframe_batch", {"symbols": symbols, "timeframes": ["1D"]})
        payload = raw.get("result", {}).get("content") if isinstance(raw, dict) else raw
        parsed, warnings = parse_mcp_text_payload(payload)
    except Exception as exc:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"error: {exc}")
        return 1

    top_keys = list(parsed.keys()) if isinstance(parsed, dict) else []
    data = parsed.get("data") if isinstance(parsed, dict) else None
    data_keys = list(data.keys()) if isinstance(data, dict) else []
    results = data.get("results") if isinstance(data, dict) else None
    sample_key, sample_value = _first_symbol_sample(results, symbols)
    timeframe_sample = None
    if isinstance(sample_value, dict):
        tf_map = sample_value.get("timeframes")
        if isinstance(tf_map, dict):
            timeframe_sample = tf_map.get("1D")
    numeric_fields = sorted(_collect_numeric_fields(timeframe_sample)) if timeframe_sample is not None else []

    report = {
        "requested_symbols": symbols,
        "warnings": warnings,
        "top_level_keys": top_keys,
        "has_summary_markdown": bool(isinstance(parsed, dict) and parsed.get("summary_markdown")),
        "data_type": type(data).__name__,
        "data_keys": data_keys,
        "results_keys": list(results.keys()) if isinstance(results, dict) else [],
        "first_symbol_key": sample_key,
        "first_symbol_sample": _sanitize(sample_value),
        "first_symbol_timeframe_1d": _sanitize(timeframe_sample),
        "numeric_fields_found": numeric_fields,
        "sanitized_response": _sanitize(parsed),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("top-level keys:", top_keys)
    print("summary_markdown existe:", report["has_summary_markdown"])
    print("tipo de data:", report["data_type"])
    print("keys de data:", data_keys)
    print("ejemplo reducido del primer símbolo:", _sanitize(sample_value) if isinstance(sample_value, dict) else sample_value)
    print("ejemplo timeframe 1D:", _sanitize(timeframe_sample) if isinstance(timeframe_sample, dict) else timeframe_sample)
    print("campos numéricos encontrados:", numeric_fields)
    print(f"Salida guardada en: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
