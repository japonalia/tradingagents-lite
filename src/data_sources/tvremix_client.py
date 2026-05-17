from __future__ import annotations

import os
import json
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from src.data_sources.base import MarketDataResult

DEFAULT_TVREMIX_MCP_URL = "https://tvremix.xyz/api/mcp/v1"
MISSING_CONFIG_MESSAGE = (
    "TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY."
)

load_dotenv()


def _get_tvremix_config() -> tuple[str | None, str | None]:
    raw_url = os.getenv("TVREMIX_MCP_URL", "").strip()
    raw_key = os.getenv("TVREMIX_API_KEY", "").strip()

    url = raw_url or DEFAULT_TVREMIX_MCP_URL
    api_key = raw_key or None
    return url, api_key


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def normalize_tv_symbol(symbol: str) -> str:
    normalized = symbol.upper().strip()
    if not normalized:
        raise ValueError("El ticker no puede estar vacío.")
    if ":" in normalized:
        return normalized
    return f"NASDAQ:{normalized}"


def call_tool(tool_name: str, arguments: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    url, api_key = _get_tvremix_config()
    if not url or not api_key:
        raise ValueError(MISSING_CONFIG_MESSAGE)

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    try:
        response = requests.post(
            url,
            headers=_build_headers(api_key),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"TVRemix MCP tools/call falló ({tool_name}): {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(
            f"TVRemix MCP tools/call devolvió JSON inválido ({tool_name}): {exc}"
        ) from exc

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"TVRemix tools/call error ({tool_name}): {data['error']}")

    return data


def _extract_result_payload(payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if isinstance(result, dict):
        if "content" in result:
            return result.get("content")
        if "data" in result:
            return result.get("data")
    return result


def parse_mcp_text_payload(payload: Any) -> tuple[Any, list[str]]:
    warnings: list[str] = []

    def _try_json(text: str, context: str) -> Any:
        try:
            return json.loads(text)
        except (TypeError, json.JSONDecodeError):
            warnings.append(f"{context}: texto no es JSON válido; se conserva texto original.")
            return text

    if payload is None:
        return None, warnings

    if isinstance(payload, str):
        return _try_json(payload, "payload string"), warnings

    if isinstance(payload, list):
        text_blocks: list[str] = []
        dict_items: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                dict_items.append(item)
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_blocks.append(item["text"])
            elif isinstance(item, str):
                text_blocks.append(item)
        if text_blocks:
            parsed_blocks = [_try_json(block, "bloque content.text") for block in text_blocks]
            return parsed_blocks[0] if len(parsed_blocks) == 1 else parsed_blocks, warnings
        if dict_items:
            return dict_items, warnings
        return payload, warnings

    if isinstance(payload, dict):
        if payload.get("type") == "text":
            text = payload.get("text")
            if isinstance(text, str):
                return _try_json(text, "payload type=text"), warnings
            warnings.append("payload type=text sin campo text válido.")
            return payload, warnings

        content = payload.get("content")
        if isinstance(content, list):
            parsed_content, content_warnings = parse_mcp_text_payload(content)
            warnings.extend(content_warnings)
            if parsed_content is not None:
                return parsed_content, warnings

        if isinstance(payload.get("text"), str):
            return _try_json(payload["text"], "payload.text"), warnings

        return payload, warnings

    return payload, warnings


def _to_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def _extract_news_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "news", "headlines", "data", "results"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [x for x in candidate if isinstance(x, dict)]
    return []


def _extract_ohlcv_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("bars", "items", "candles", "ohlcv", "data", "results"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [x for x in candidate if isinstance(x, dict)]
    return []


def fetch_quote(symbol: str) -> tuple[dict[str, Any], list[str]]:
    raw = _extract_result_payload(call_tool("get_quote", {"symbol": symbol}))
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    quote = _to_record(parsed)
    warnings = parse_warnings
    if not quote:
        warnings.append(
            f"get_quote sin payload parseable. raw_keys={list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}"
        )
    return quote, warnings


def fetch_technicals(symbol: str, interval: str = "1D") -> tuple[dict[str, Any], list[str]]:
    raw = _extract_result_payload(
        call_tool("get_technicals", {"symbol": symbol, "interval": interval})
    )
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    technicals = _to_record(parsed)
    warnings = parse_warnings
    if not technicals:
        warnings.append(
            f"get_technicals sin payload parseable. raw_keys={list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}"
        )
    return technicals, warnings


def fetch_financials(symbol: str) -> tuple[dict[str, Any], list[str]]:
    raw = _extract_result_payload(call_tool("get_financials", {"symbol": symbol}))
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    financials = _to_record(parsed)
    warnings = parse_warnings
    if not financials:
        warnings.append(
            f"get_financials sin payload parseable. raw_keys={list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}"
        )
    return financials, warnings


def fetch_news(symbol: str, limit: int = 5) -> tuple[list[dict[str, Any]], list[str]]:
    raw = _extract_result_payload(call_tool("get_news", {"symbol": symbol, "limit": limit}))
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    news = _extract_news_items(parsed)
    warnings = parse_warnings
    if not news:
        warnings.append(
            f"get_news sin titulares parseables (se intentó parseo text/json). raw_type={type(parsed).__name__}"
        )
    return news[:limit], warnings


def fetch_ohlcv(symbol: str, interval: str = "1D", count: int = 300) -> tuple[pd.DataFrame, list[str]]:
    raw = _extract_result_payload(
        call_tool("get_ohlcv", {"symbol": symbol, "interval": interval, "count": count})
    )
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    rows: list[dict[str, Any]] = []
    if isinstance(parsed, dict) and isinstance(parsed.get("data"), dict):
        rows = _extract_ohlcv_rows(parsed.get("data"))
    if not rows:
        rows = _extract_ohlcv_rows(parsed)
    warnings: list[str] = []
    warnings.extend(parse_warnings)
    if not rows:
        if isinstance(parsed, dict) and parsed.get("summary") is not None:
            warnings.append("get_ohlcv devolvió summary pero sin bars; no hay OHLCV completo.")
        warnings.append(
            f"get_ohlcv sin payload parseable. raw_type={type(parsed).__name__}"
        )
        return pd.DataFrame(), warnings

    history = pd.DataFrame(rows)
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "time": "Date",
        "timestamp": "Date",
        "datetime": "Date",
        "date": "Date",
        "t": "Date",
        "o": "Open",
        "h": "High",
        "l": "Low",
        "c": "Close",
        "v": "Volume",
    }
    history = history.rename(columns={k: v for k, v in rename_map.items() if k in history.columns})

    if "Date" in history.columns:
        history["Date"] = pd.to_datetime(history["Date"], errors="coerce", utc=True)
        history = history.dropna(subset=["Date"]).sort_values("Date")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in history.columns:
            history[col] = pd.to_numeric(history[col], errors="coerce")

    required = ["Open", "High", "Low", "Close"]
    if any(col not in history.columns for col in required):
        warnings.append(f"get_ohlcv sin columnas OHLC completas. columnas={list(history.columns)}")
        return pd.DataFrame(), warnings

    history = history.dropna(subset=required)
    return history, warnings


def fetch_tvremix_data(symbol: str) -> MarketDataResult:
    user_symbol = symbol.upper().strip()
    tv_symbol = normalize_tv_symbol(symbol)
    warnings: list[str] = [
        "Formato TVRemix: para mercados no NASDAQ usa formato TradingView, ej. NYSE:IBM."
    ]

    missing_fields: list[str] = []

    quote, quote_warnings = fetch_quote(tv_symbol)
    technicals, tech_warnings = fetch_technicals(tv_symbol)
    financials, fin_warnings = fetch_financials(tv_symbol)
    news_items, news_warnings = fetch_news(tv_symbol, limit=5)
    history, ohlcv_warnings = fetch_ohlcv(tv_symbol, interval="1D", count=300)

    warnings.extend(quote_warnings + tech_warnings + fin_warnings + news_warnings + ohlcv_warnings)

    quote_data = quote.get("data", {}) if isinstance(quote.get("data"), dict) else quote
    technicals_data = (
        technicals.get("data", {}) if isinstance(technicals.get("data"), dict) else technicals
    )
    financials_data = (
        financials.get("data", {}) if isinstance(financials.get("data"), dict) else financials
    )

    tech_summary = technicals_data.get("summary", {}) if isinstance(technicals_data, dict) else {}
    tech_osc = technicals_data.get("oscillators", {}) if isinstance(technicals_data, dict) else {}

    if isinstance(quote.get("data"), dict):
        expected_quote_fields = [
            "price",
            "change_abs",
            "change_percent",
            "volume",
            "market_cap",
            "pe_ratio",
            "sector",
            "industry",
            "name",
            "description",
        ]
        missing_quote_fields = [field for field in expected_quote_fields if field not in quote_data]
        if missing_quote_fields:
            warnings.append(
                "get_quote.data sin campos esperados: " + ", ".join(sorted(missing_quote_fields))
            )

    if isinstance(financials.get("data"), dict):
        known_financial_fields = {"eps", "revenue", "ebitda", "debt", "sector", "industry", "pe_ratio", "market_cap"}
        if not any(field in financials_data for field in known_financial_fields):
            warnings.append(
                "get_financials.data con nombres no mapeados. keys="
                + ", ".join(sorted(financials_data.keys()))
            )

    market_data: dict[str, Any] = {
        "tv_symbol": tv_symbol,
        "quote": quote,
        "technicals": technicals,
        "financials": financials,
        "news": news_items,
        "last_price": quote_data.get("price") or quote.get("last_price") or quote.get("price") or quote.get("close"),
        "change_abs": quote_data.get("change_abs") or quote.get("change_abs") or quote.get("change"),
        "change_percent": quote_data.get("change_percent") or quote.get("change_percent"),
        "volume": quote_data.get("volume") or quote.get("volume"),
        "market_cap": quote_data.get("market_cap") or quote.get("market_cap") or financials_data.get("market_cap") or financials.get("market_cap") or financials.get("marketCap"),
        "pe_ratio": quote_data.get("pe_ratio") or quote.get("pe_ratio") or financials_data.get("pe_ratio") or financials.get("pe_ratio") or financials.get("pe") or financials.get("trailing_pe"),
        "eps": financials_data.get("eps") or financials.get("eps"),
        "revenue": financials_data.get("revenue") or financials.get("revenue"),
        "ebitda": financials_data.get("ebitda") or financials.get("ebitda"),
        "debt": financials_data.get("debt") or financials.get("debt"),
        "sector": quote_data.get("sector") or quote.get("sector") or financials_data.get("sector") or financials.get("sector"),
        "industry": quote_data.get("industry") or quote.get("industry") or financials_data.get("industry") or financials.get("industry"),
        "name": quote_data.get("name") or quote.get("name"),
        "description": quote_data.get("description") or quote.get("description"),
        "technical_rating": tech_summary.get("recommendation"),
        "technical_rating_value": tech_summary.get("value"),
        "tvremix_rsi": tech_osc.get("rsi"),
        "technical_price": technicals_data.get("price"),
        "technical_change": technicals_data.get("change"),
        "technical_volume": technicals_data.get("volume"),
        "rsi": tech_osc.get("rsi") or technicals_data.get("rsi") or technicals.get("rsi"),
        "ohlcv_rows": len(history),
    }

    for key in ("last_price", "volume", "market_cap", "pe_ratio", "eps"):
        if market_data.get(key) is None:
            missing_fields.append(key)

    if not quote and not financials and not news_items and history.empty:
        raise RuntimeError("TVRemix MCP no devolvió datos utilizables; se aplicará fallback a yfinance.")

    return MarketDataResult(
        symbol=user_symbol,
        source="tvremix",
        market_data=market_data,
        history=history,
        missing_fields=missing_fields,
        warnings=warnings,
    )
