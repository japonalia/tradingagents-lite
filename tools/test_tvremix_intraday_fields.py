from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data_sources.tvremix_client import (
    call_tool,
    normalize_tv_symbol,
    parse_mcp_text_payload,
)

SYMBOLS = [
    "NASDAQ:NVDA",
    "NASDAQ:MSFT",
    "NASDAQ:TSLA",
    "NASDAQ:ZS",
    "NASDAQ:QQQ",
]
TIMEFRAMES = ["5m", "15m", "1h", "1D"]
OHLCV_INTERVALS = ["1m", "5m", "15m", "1D"]
OUTPUT_PATH = Path("reports/generated/tvremix_intraday_fields_test.json")

CANDIDATE_COLUMNS = [
    "close",
    "change",
    "change_abs",
    "volume",
    "relative_volume_10d_calc",
    "relative_volume_intraday_5m",
    "average_volume_10d_calc",
    "VWAP",
    "premarket_change",
    "premarket_gap",
    "premarket_high",
    "premarket_low",
    "gap",
    "market_cap_basic",
    "price_earnings_ttm",
]

SCREENER_COLUMNS = [
    "close",
    "change",
    "change_abs",
    "volume",
    "relative_volume_10d_calc",
    "average_volume_10d_calc",
    "VWAP",
    "premarket_change",
    "premarket_gap",
    "premarket_high",
    "premarket_low",
    "gap",
]

FIELD_HINTS = [
    "volume",
    "average_volume",
    "relative_volume",
    "rvol",
    "vwap",
    "premarket",
    "extended",
    "open",
    "high",
    "low",
    "close",
    "gap",
    "change",
    "qqq",
    "timestamp",
    "time",
    "bar",
]
SYMBOL_CANDIDATE_FIELDS = [
    "symbol",
    "ticker",
    "name",
    "description",
    "exchange",
    "prefix",
    "listed_exchange",
    "update_mode",
    "logoid",
    "root",
    "base_name",
    "short_name",
    "pro_name",
]


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)
    return obj


def _extract_payload(raw: dict[str, Any]) -> tuple[Any, list[str]]:
    result = raw.get("result") if isinstance(raw, dict) else None
    payload = result
    if isinstance(result, dict):
        payload = result.get("content", result.get("data", result))
    parsed, warnings = parse_mcp_text_payload(payload)
    return parsed, warnings


def _collect_matching_fields(payload: Any, hints: list[str], limit: int = 200) -> list[str]:
    matches: set[str] = set()

    def visit(node: Any, prefix: str = "") -> None:
        if len(matches) >= limit:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k)
                path = f"{prefix}.{key}" if prefix else key
                lk = key.lower()
                if any(h in lk for h in hints):
                    matches.add(path)
                visit(v, path)
        elif isinstance(node, list):
            for idx, item in enumerate(node[:10]):
                visit(item, f"{prefix}[{idx}]" if prefix else f"[{idx}]")

    visit(payload)
    return sorted(matches)


def _try_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = call_tool(tool_name, arguments)
        parsed, parse_warnings = _extract_payload(raw)
        return {
            "status": "ok",
            "arguments": arguments,
            "parse_warnings": parse_warnings,
            "top_level_keys": list(parsed.keys()) if isinstance(parsed, dict) else [],
            "matching_fields": _collect_matching_fields(parsed, FIELD_HINTS),
            "payload_preview": _sanitize(parsed),
        }
    except Exception as exc:
        return {"status": "error", "arguments": arguments, "error": str(exc)}


def _ohlcv_summary(symbol: str, interval: str) -> dict[str, Any]:
    result = _try_tool("get_ohlcv", {"symbol": symbol, "interval": interval, "count": 50})
    if result.get("status") != "ok":
        return result

    payload = result.get("payload_preview")
    bars: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("bars", "items", "candles", "ohlcv", "data", "results"):
                if isinstance(data.get(key), list):
                    bars = [x for x in data[key] if isinstance(x, dict)]
                    break
        if not bars:
            for key in ("bars", "items", "candles", "ohlcv", "data", "results"):
                if isinstance(payload.get(key), list):
                    bars = [x for x in payload[key] if isinstance(x, dict)]
                    break

    first_ts = None
    last_ts = None
    sample_fields: list[str] = []
    has_volume = False
    approx_vwap_possible = False
    if bars:
        sample = bars[0]
        sample_fields = sorted(sample.keys())
        ts_keys = ["time", "timestamp", "datetime", "date", "t"]
        for key in ts_keys:
            if key in bars[0]:
                first_ts = bars[0].get(key)
                last_ts = bars[-1].get(key)
                break
        has_volume = any(("volume" in b or "v" in b) for b in bars)
        price_keys = any(any(k in b for k in ("close", "c", "high", "h", "low", "l")) for b in bars)
        approx_vwap_possible = has_volume and price_keys

    return {
        "status": "ok",
        "arguments": result.get("arguments"),
        "parse_warnings": result.get("parse_warnings", []),
        "top_level_keys": result.get("top_level_keys", []),
        "matching_fields": result.get("matching_fields", []),
        "summary": {
            "bars_count": len(bars),
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "sample_bar_fields": sample_fields,
            "has_volume": has_volume,
            "approx_vwap_possible_from_bars": approx_vwap_possible,
        },
    }


def main() -> int:
    symbols = [normalize_tv_symbol(s) for s in SYMBOLS]
    report: dict[str, Any] = {
        "purpose": "Diagnóstico experimental de campos intradía en TVRemix.",
        "symbols": symbols,
        "tools": {},
        "warnings": [],
    }

    report["tools"]["get_quote"] = {
        s: _try_tool("get_quote", {"symbol": s}) for s in symbols
    }

    report["tools"]["get_symbol_data"] = {
        "status_by_symbol": {
            s: _try_tool("get_symbol_data", {"symbol": s, "columns": CANDIDATE_COLUMNS})
            for s in symbols
        },
        "candidate_columns": CANDIDATE_COLUMNS,
    }

    run_screener_result = _try_tool(
        "run_screener",
        {
            "market": "america",
            "limit": 5,
            "columns": SCREENER_COLUMNS,
        },
    )
    payload_preview = run_screener_result.get("payload_preview")
    results_rows: list[dict[str, Any]] = []
    if isinstance(payload_preview, dict):
        data = payload_preview.get("data")
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            results_rows = [x for x in data.get("results", []) if isinstance(x, dict)]
        elif isinstance(payload_preview.get("results"), list):
            results_rows = [x for x in payload_preview.get("results", []) if isinstance(x, dict)]
    if results_rows:
        sample_row = results_rows[0]
        run_screener_result["rows_returned"] = len(results_rows)
        run_screener_result["sample_row_keys"] = sorted(sample_row.keys())
        run_screener_result["sample_row_compact"] = {
            k: sample_row.get(k) for k in sorted(sample_row.keys())[:20]
        }
        run_screener_result["symbol_candidate_fields_detected"] = {
            f: sample_row.get(f)
            for f in SYMBOL_CANDIDATE_FIELDS
            if sample_row.get(f) not in (None, "")
        }
    report["tools"]["run_screener"] = run_screener_result

    report["tools"]["analyze_multi_timeframe_batch"] = _try_tool(
        "analyze_multi_timeframe_batch",
        {"symbols": symbols, "timeframes": TIMEFRAMES},
    )

    report["tools"]["get_ohlcv"] = {
        s: {interval: _ohlcv_summary(s, interval) for interval in OHLCV_INTERVALS} for s in symbols
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(_sanitize(report), ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Diagnóstico intradía TVRemix ===")
    print(f"Símbolos: {', '.join(symbols)}")
    print("Tools probadas: get_quote, get_symbol_data, run_screener, analyze_multi_timeframe_batch, get_ohlcv")

    for tool_name, tool_payload in report["tools"].items():
        print(f"\n[{tool_name}]")
        if isinstance(tool_payload, dict) and "status" in tool_payload:
            print(f"  status: {tool_payload.get('status')}")
            print(f"  top_level_keys: {tool_payload.get('top_level_keys', [])}")
            print(f"  matching_fields: {tool_payload.get('matching_fields', [])[:20]}")
            if tool_name == "run_screener":
                print(f"  rows_returned: {tool_payload.get('rows_returned')}")
                print(f"  data.results[0].keys: {tool_payload.get('sample_row_keys', [])}")
                print(
                    f"  symbol_candidate_fields_detected: {tool_payload.get('symbol_candidate_fields_detected', {})}"
                )
            continue

        if tool_name == "get_ohlcv":
            ok = 0
            total = 0
            for symbol_data in tool_payload.values():
                for interval_data in symbol_data.values():
                    total += 1
                    if interval_data.get("status") == "ok":
                        ok += 1
            print(f"  status: {ok}/{total} combinaciones OK")
            sample = tool_payload[symbols[0]][OHLCV_INTERVALS[0]]
            print(f"  ejemplo top_level_keys: {sample.get('top_level_keys', [])}")
            print(f"  ejemplo resumen barras: {sample.get('summary', {})}")
        elif tool_name == "get_symbol_data":
            statuses = {
                s: data.get("status")
                for s, data in tool_payload.get("status_by_symbol", {}).items()
            }
            print(f"  status por símbolo: {statuses}")
        else:
            print("  payload agregado por símbolo (ver JSON para detalle).")

    print(f"\nSalida guardada en: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
