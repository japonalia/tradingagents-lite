from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_sources.tvremix_client import _extract_result_payload, call_tool, parse_mcp_text_payload

SYMBOLS = ["NASDAQ:DXCM", "NASDAQ:MU", "NASDAQ:ARM", "NASDAQ:MRVL", "NASDAQ:NVDA"]
OUT = Path("reports/generated/tvremix_news_fields_test.json")


def looks_like_json_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    t = value.strip()
    return (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]"))


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items() if str(k).lower() != "authorization"}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str) and "TVREMIX_API_KEY" in value:
        return value.replace("TVREMIX_API_KEY", "***")
    return value


def inspect_symbol(symbol: str) -> dict[str, Any]:
    raw = call_tool("get_news", {"symbol": symbol, "limit": 5})
    payload = _extract_result_payload(raw)
    parsed, warnings = parse_mcp_text_payload(payload)

    top_keys = list(raw.keys()) if isinstance(raw, dict) else []
    payload_type = type(payload).__name__
    parsed_type = type(parsed).__name__

    relevant_keys = []
    content_text_present = False
    content_text_json_like = False
    headline_fields = []

    if isinstance(parsed, dict):
        relevant_keys = [k for k in parsed.keys() if k in {"items", "news", "headlines", "data", "results", "content", "text"}]
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                content_text_present = True
                content_text_json_like = content_text_json_like or looks_like_json_text(item.get("text"))
    elif isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    content_text_present = True
                    content_text_json_like = content_text_json_like or looks_like_json_text(block.get("text"))

    scan_items = []
    if isinstance(parsed, list):
        scan_items = [x for x in parsed if isinstance(x, dict)]
    elif isinstance(parsed, dict):
        for key in ("items", "news", "headlines", "data", "results"):
            if isinstance(parsed.get(key), list):
                scan_items = [x for x in parsed.get(key) if isinstance(x, dict)]
                break

    wanted = ["title", "headline", "published", "provider", "source", "url", "summary"]
    for item in scan_items[:5]:
        found = {k: item.get(k) for k in wanted if item.get(k) not in (None, "")}
        if found:
            headline_fields.append(found)

    print(f"\n[{symbol}]")
    print(f"top-level keys: {top_keys}")
    print(f"payload_type={payload_type}, parsed_type={parsed_type}")
    print(f"relevant keys: {relevant_keys}")
    print(f"content.text present: {content_text_present}")
    print(f"content.text parece JSON: {content_text_json_like}")
    print(f"campos titulares detectados: {headline_fields[:2] if headline_fields else 'ninguno'}")

    return {
        "symbol": symbol,
        "top_level_keys": top_keys,
        "payload_type": payload_type,
        "parsed_type": parsed_type,
        "relevant_keys": relevant_keys,
        "content_text_present": content_text_present,
        "content_text_json_like": content_text_json_like,
        "headline_fields_detected": headline_fields,
        "warnings": warnings,
        "raw": sanitize(raw),
        "payload": sanitize(payload),
        "parsed": sanitize(parsed),
    }


def main() -> None:
    rows = []
    for symbol in SYMBOLS:
        try:
            rows.append(inspect_symbol(symbol))
        except Exception as exc:
            rows.append({"symbol": symbol, "error": str(exc)})
            print(f"[{symbol}] error: {exc}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado: {OUT}")


if __name__ == "__main__":
    main()
