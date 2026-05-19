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




def _extract_earnings_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "earnings", "calendar", "data", "results"):
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


def fetch_quotes_batch(symbols: list[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    normalized = [normalize_tv_symbol(symbol) for symbol in symbols if str(symbol).strip()]
    if not normalized:
        return {}, ["No se recibieron símbolos para get_quotes_batch."]
    chunk_size = 50
    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    failed_chunks = 0

    for idx in range(0, len(normalized), chunk_size):
        chunk = normalized[idx : idx + chunk_size]
        chunk_number = (idx // chunk_size) + 1
        try:
            raw = _extract_result_payload(call_tool("get_quotes_batch", {"symbols": chunk}))
            parsed, parse_warnings = parse_mcp_text_payload(raw)
            chunk_records = normalize_quote_batch_payload(parsed, chunk)
            warnings.extend(parse_warnings)
            if not chunk_records:
                failed_chunks += 1
                warnings.append(
                    f"get_quotes_batch chunk {chunk_number} sin payload parseable (size={len(chunk)})."
                )
            else:
                records.update(chunk_records)
        except Exception as exc:
            failed_chunks += 1
            warnings.append(
                f"get_quotes_batch chunk {chunk_number} falló (size={len(chunk)}): {exc}"
            )

    if failed_chunks and not records:
        warnings.append("get_quotes_batch sin payload parseable en todos los chunks.")

    return records, warnings


def normalize_quote_batch_payload(
    payload: Any, requested_symbols: list[str]
) -> dict[str, dict[str, Any]]:
    def _core(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        if isinstance(value.get("data"), dict):
            return value["data"]
        return value

    def _quote_subset(value: Any) -> dict[str, Any]:
        quote = _core(value)
        if not quote:
            return {}
        return {
            "price": quote.get("price") or quote.get("last_price") or quote.get("close"),
            "change_percent": quote.get("change_percent"),
            "volume": quote.get("volume"),
            "market_cap": quote.get("market_cap"),
            "pe_ratio": quote.get("pe_ratio"),
        }

    requested_tv = {normalize_tv_symbol(symbol).upper() for symbol in requested_symbols}
    requested_short = {symbol.split(":", 1)[-1].upper() for symbol in requested_tv}
    alias_to_tv = {
        symbol.split(":", 1)[-1].upper(): symbol
        for symbol in requested_tv
    }

    by_symbol: dict[str, dict[str, Any]] = {}

    def _bind(symbol_key: str, quote_value: Any) -> None:
        normalized_key = str(symbol_key).upper().strip()
        if not normalized_key:
            return
        mapped = normalized_key if ":" in normalized_key else alias_to_tv.get(normalized_key)
        if not mapped and normalized_key in requested_tv:
            mapped = normalized_key
        if not mapped:
            return
        by_symbol[mapped] = _quote_subset(quote_value)

    if isinstance(payload, dict):
        source = payload.get("data")
    else:
        source = payload

    if isinstance(source, list):
        for item in source:
            if isinstance(item, dict):
                key = (
                    item.get("symbol")
                    or item.get("ticker")
                    or item.get("name")
                    or item.get("tv_symbol")
                )
                _bind(str(key or ""), item)
    elif isinstance(source, dict):
        for key, value in source.items():
            if isinstance(value, dict):
                _bind(str(key), value)

    records: dict[str, dict[str, Any]] = {}
    for tv_symbol in requested_tv:
        short = tv_symbol.split(":", 1)[-1].upper()
        quote_data = by_symbol.get(tv_symbol) or by_symbol.get(alias_to_tv.get(short, ""))
        if quote_data:
            records[tv_symbol] = quote_data
            records[short] = quote_data
    # Solo incluir claves ya solicitadas.
    return {
        key: value
        for key, value in records.items()
        if key in requested_tv or key in requested_short
    }


def _extract_screener_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "rows", "symbols"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [x for x in candidate if isinstance(x, dict)]
    return []


def fetch_intraday_screener_fields(
    symbols: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    normalized = [normalize_tv_symbol(symbol) for symbol in symbols if str(symbol).strip()]
    if not normalized:
        return {}, ["No se recibieron símbolos para run_screener."], {}
    requested_tv = {sym.upper() for sym in normalized}
    requested_short = {sym.split(":", 1)[-1].upper() for sym in requested_tv}
    short_to_tv = {sym.split(":", 1)[-1].upper(): sym for sym in requested_tv}

    arguments = {
        "market": "america",
        "sortBy": "relative_volume_10d_calc",
        "sortOrder": "desc",
        "limit": max(300, len(normalized) * 4),
        "columns": [
            "name",
            "close",
            "change",
            "change_abs",
            "volume",
            "average_volume_10d_calc",
            "relative_volume_10d_calc",
            "VWAP",
            "premarket_change",
            "premarket_gap",
            "premarket_high",
            "premarket_low",
            "gap",
            "market_cap_basic",
            "price_earnings_ttm",
        ],
    }

    try:
        raw = _extract_result_payload(call_tool("run_screener", arguments))
        parsed, warnings = parse_mcp_text_payload(raw)
    except Exception as exc:
        return {}, [f"run_screener falló: {exc}"], {}

    items = _extract_screener_items(parsed)
    records: dict[str, dict[str, Any]] = {}
    detected_symbol_fields: set[str] = set()

    candidate_fields = [
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

    def _normalize_exchange(value: Any) -> str | None:
        if value in (None, ""):
            return None
        exchange = str(value).strip().upper()
        if not exchange:
            return None
        if exchange in {"NAS", "XNAS"}:
            return "NASDAQ"
        return exchange

    def _symbol_variants(item: dict[str, Any]) -> list[str]:
        variants: set[str] = set()
        exchange = _normalize_exchange(
            item.get("exchange") or item.get("prefix") or item.get("listed_exchange")
        )
        for field in candidate_fields:
            value = item.get(field)
            if value in (None, ""):
                continue
            detected_symbol_fields.add(field)
            token = str(value).strip().upper()
            if not token:
                continue
            if ":" in token:
                left, right = token.split(":", 1)
                left = left.strip().upper()
                right = right.strip().upper()
                if right:
                    variants.add(f"{left}:{right}")
                    variants.add(right)
                continue
            if token.isalpha() and 1 <= len(token) <= 8:
                variants.add(token)
                if exchange:
                    variants.add(f"{exchange}:{token}")
                if token in short_to_tv:
                    variants.add(short_to_tv[token])
                    variants.add(f"NASDAQ:{token}")
        return sorted(variants)

    for item in items:
        variants = _symbol_variants(item)
        mapped_tv: str | None = None
        mapped_short: str | None = None
        for variant in variants:
            if variant in requested_tv:
                mapped_tv = variant
                mapped_short = variant.split(":", 1)[-1].upper()
                break
            short = variant.split(":", 1)[-1].upper()
            if short in requested_short:
                mapped_short = short
                mapped_tv = short_to_tv.get(short) or f"NASDAQ:{short}"
                break
        if not mapped_tv or not mapped_short:
            continue
        records[mapped_tv] = item
        records[mapped_short] = item

    matched_short = {k for k in records if ":" not in k}
    matched_count = len(matched_short)
    requested_count = len(requested_short)
    if not records:
        warnings.append("run_screener sin símbolos parseables del universo solicitado.")
    if matched_count < requested_count:
        warnings.append(
            f"run_screener devolvió intradía para {matched_count}/{requested_count} símbolos del universo."
        )

    diagnostics = {
        "screener_rows_returned": len(items),
        "screener_symbols_matched": matched_count,
        "screener_symbol_fields_detected": sorted(detected_symbol_fields),
    }
    return records, warnings, diagnostics


def fetch_intraday_symbol_data_batch(
    symbols: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    normalized = [normalize_tv_symbol(symbol) for symbol in symbols if str(symbol).strip()]
    if not normalized:
        return {}, ["No se recibieron símbolos para get_symbol_data."], {}

    requested_tv = {sym.upper() for sym in normalized}
    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    success_count = 0
    failed_count = 0

    columns = [
        "close",
        "change",
        "change_abs",
        "volume",
        "average_volume_10d_calc",
        "relative_volume_10d_calc",
        "vol_ratio_10d",
        "VWAP",
        "premarket_change",
        "premarket_gap",
        "premarket_high",
        "premarket_low",
        "gap",
        "market_cap_basic",
        "price_earnings_ttm",
        "days_to_earnings",
        "price_vs_ema50_pct",
        "price_vs_ema200_pct",
    ]

    def _extract_symbol_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), dict):
                return payload["data"]
            for key in ("symbol_data", "symbol", "result"):
                candidate = payload.get(key)
                if isinstance(candidate, dict):
                    return candidate
            return payload
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    return item
        return {}

    for tv_symbol in normalized:
        short = tv_symbol.split(":", 1)[-1].upper()
        try:
            raw = _extract_result_payload(
                call_tool("get_symbol_data", {"symbol": tv_symbol, "columns": columns})
            )
            parsed, parse_warnings = parse_mcp_text_payload(raw)
            warnings.extend(parse_warnings)
            data = _extract_symbol_payload(parsed)
            if not data:
                failed_count += 1
                warnings.append(f"get_symbol_data sin payload parseable para {tv_symbol}.")
                continue
            compact = {
                "intraday_close": data.get("close"),
                "intraday_change": data.get("change"),
                "intraday_change_abs": data.get("change_abs"),
                "intraday_volume": data.get("volume"),
                "avg_volume_10d": data.get("average_volume_10d_calc"),
                "rvol_10d": data.get("relative_volume_10d_calc")
                if data.get("relative_volume_10d_calc") not in (None, "")
                else data.get("vol_ratio_10d"),
                "vwap": data.get("VWAP"),
                "premarket_change": data.get("premarket_change"),
                "premarket_gap": data.get("premarket_gap"),
                "premarket_high": data.get("premarket_high"),
                "premarket_low": data.get("premarket_low"),
                "gap": data.get("gap"),
                "days_to_earnings": data.get("days_to_earnings"),
                "price_vs_ema50_pct": data.get("price_vs_ema50_pct"),
                "price_vs_ema200_pct": data.get("price_vs_ema200_pct"),
                "market_cap_basic": data.get("market_cap_basic"),
                "price_earnings_ttm": data.get("price_earnings_ttm"),
            }
            records[tv_symbol.upper()] = compact
            records[short] = compact
            success_count += 1
        except Exception as exc:
            failed_count += 1
            warnings.append(f"get_symbol_data falló para {tv_symbol}: {exc}")
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                warnings.append("rate limit alcanzado en get_symbol_data; se detuvieron consultas adicionales")
                break

    diagnostics = {
        "symbol_data_requested": len(requested_tv),
        "symbol_data_success": success_count,
        "symbol_data_failed": failed_count,
    }
    return records, warnings, diagnostics


def fetch_technicals_batch(symbols: list[str], interval: str = "1D") -> tuple[dict[str, dict[str, Any]], list[str]]:
    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        tv_symbol = normalize_tv_symbol(symbol)
        try:
            technicals, tech_warnings = fetch_technicals(tv_symbol, interval=interval)
            records[tv_symbol.upper()] = technicals
            warnings.extend(tech_warnings)
        except Exception as exc:
            warnings.append(f"get_technicals falló para {tv_symbol}: {exc}")
    return records, warnings


def fetch_multi_timeframe_technicals_batch(
    symbols: list[str], timeframes: list[str] | None = None
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    normalized = [normalize_tv_symbol(symbol) for symbol in symbols if str(symbol).strip()]
    if not normalized:
        return {}, ["No se recibieron símbolos para analyze_multi_timeframe_batch."]

    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    timeframe_list = timeframes or ["1D"]

    raw = _extract_result_payload(
        call_tool(
            "analyze_multi_timeframe_batch",
            {"symbols": normalized, "timeframes": timeframe_list},
        )
    )
    parsed, parse_warnings = parse_mcp_text_payload(raw)
    warnings.extend(parse_warnings)

    requested_tv = {symbol.upper() for symbol in normalized}
    requested_short = {symbol.split(":", 1)[-1].upper() for symbol in requested_tv}
    key_lookup = {symbol.split(":", 1)[-1].upper(): symbol for symbol in requested_tv}

    def _as_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value.strip())
            except Exception:
                return value
        return value

    def _collect_symbol_record(symbol_key: str, item: Any, summary_text: str | None = None) -> None:
        if not isinstance(item, dict):
            return
        normalized_key = str(symbol_key or "").upper().strip()
        if not normalized_key:
            return
        mapped_tv = normalized_key if ":" in normalized_key else key_lookup.get(normalized_key)
        if not mapped_tv:
            return

        price = item.get("price") if isinstance(item.get("price"), dict) else {}
        timeframes = item.get("timeframes") if isinstance(item.get("timeframes"), dict) else {}
        timeframe = timeframes.get("1D") if isinstance(timeframes.get("1D"), dict) else {}
        rating = timeframe.get("rating") if isinstance(timeframe.get("rating"), dict) else {}
        oscillators = timeframe.get("oscillators") if isinstance(timeframe.get("oscillators"), dict) else {}
        moving_averages = (
            timeframe.get("moving_averages")
            if isinstance(timeframe.get("moving_averages"), dict)
            else {}
        )
        confluence = item.get("confluence") if isinstance(item.get("confluence"), dict) else {}
        timeframe_bollinger = timeframe.get("bollinger") if isinstance(timeframe.get("bollinger"), dict) else {}
        root_bollinger = item.get("bollinger") if isinstance(item.get("bollinger"), dict) else {}
        bollinger = timeframe_bollinger or root_bollinger

        compact = {
            "timeframe": "1D",
            "summary_markdown": summary_text,
            "technical_price": _as_number(price.get("price")),
            "technical_open": _as_number(price.get("open")),
            "technical_high": _as_number(price.get("high")),
            "technical_low": _as_number(price.get("low")),
            "technical_change": _as_number(price.get("change")),
            "technical_volume": _as_number(price.get("volume")),
            "week_52_high": _as_number(price.get("week_52_high")),
            "week_52_low": _as_number(price.get("week_52_low")),
            "market_cap": _as_number(price.get("market_cap")),
            "technical_rating": rating.get("summary"),
            "technical_rating_value": _as_number(rating.get("value")),
            "ma_bias": rating.get("moving_averages"),
            "oscillator_bias": rating.get("oscillators"),
            "rsi": _as_number(oscillators.get("rsi")),
            "macd": _as_number(oscillators.get("macd")),
            "macd_signal": _as_number(oscillators.get("macd_signal")),
            "adx": _as_number(oscillators.get("adx")),
            "stoch_k": _as_number(oscillators.get("stoch_k")),
            "cci": _as_number(oscillators.get("cci")),
            "ema10": _as_number(moving_averages.get("ema10")),
            "ema20": _as_number(moving_averages.get("ema20")),
            "ema50": _as_number(moving_averages.get("ema50")),
            "sma50": _as_number(moving_averages.get("sma50")),
            "sma100": _as_number(moving_averages.get("sma100")),
            "sma200": _as_number(moving_averages.get("sma200")),
            "atr": _as_number(timeframe.get("atr")),
            "bb_upper": _as_number(bollinger.get("upper")),
            "bb_lower": _as_number(bollinger.get("lower")),
            "confluence_alignment": confluence.get("alignment"),
        }
        compact = {k: v for k, v in compact.items() if v not in (None, "")}
        if compact:
            records[mapped_tv] = compact
            records[mapped_tv.split(":", 1)[-1].upper()] = compact

    summary_markdown = parsed.get("summary_markdown") if isinstance(parsed, dict) else None

    if isinstance(parsed, dict):
        data_root = parsed.get("data") if isinstance(parsed.get("data"), dict) else {}
        results = data_root.get("results") if isinstance(data_root.get("results"), dict) else {}
        for key, value in results.items():
            _collect_symbol_record(str(key), value, summary_markdown)

    if not records:
        raw_keys = list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__
        warnings.append(f"analyze_multi_timeframe_batch schema no mapeado. raw_keys={raw_keys}")

    return {
        key: value
        for key, value in records.items()
        if key in requested_tv or key in requested_short
    }, warnings


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



def fetch_news_for_symbols(symbols: list[str], limit_per_symbol: int = 3) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    warnings: list[str] = []
    news_map: dict[str, list[dict[str, Any]]] = {}
    rate_limited = False

    for symbol in symbols:
        if rate_limited:
            break
        tv_symbol = normalize_tv_symbol(symbol)
        short = tv_symbol.split(":", 1)[-1].upper()
        try:
            news, news_warnings = fetch_news(tv_symbol, limit=limit_per_symbol)
            news_map[tv_symbol.upper()] = news
            news_map[short] = news
            warnings.extend(news_warnings)
            if not news:
                warnings.append(f"{tv_symbol}: sin titulares recientes en get_news.")
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too Many Requests" in msg:
                warnings.append("rate limit alcanzado en get_news; se detienen consultas de noticias.")
                rate_limited = True
            else:
                warnings.append(f"get_news falló para {tv_symbol}: {exc}")
            news_map[tv_symbol.upper()] = []
            news_map[short] = []

    return news_map, warnings


def fetch_earnings_calendar(symbols: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    warnings: list[str] = []
    earnings_map: dict[str, list[dict[str, Any]]] = {}
    rate_limited = False

    for symbol in symbols:
        if rate_limited:
            break
        tv_symbol = normalize_tv_symbol(symbol)
        short = tv_symbol.split(":", 1)[-1].upper()
        try:
            raw = _extract_result_payload(call_tool("get_earnings_calendar", {"symbol": tv_symbol}))
            parsed, parse_warnings = parse_mcp_text_payload(raw)
            items = _extract_earnings_items(parsed)
            earnings_map[tv_symbol.upper()] = items
            earnings_map[short] = items
            warnings.extend(parse_warnings)
            if not items:
                warnings.append(f"{tv_symbol}: get_earnings_calendar sin datos parseables.")
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too Many Requests" in msg:
                warnings.append("rate limit alcanzado en get_earnings_calendar; se detienen consultas de earnings.")
                rate_limited = True
            else:
                warnings.append(f"get_earnings_calendar no disponible para {tv_symbol}: {exc}")
            earnings_map[tv_symbol.upper()] = []
            earnings_map[short] = []

    return earnings_map, warnings

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



def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_intraday_ohlcv_levels(
    symbols: list[str], interval: str = "5m", count: int = 100
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    """Fetch a small OHLCV sample per symbol and derive intraday levels.

    Intended for top candidates only; callers should keep ``symbols`` small.
    Failures are collected as warnings so scanner flows can continue.
    """
    normalized = [normalize_tv_symbol(symbol) for symbol in symbols if str(symbol).strip()]
    if not normalized:
        return {}, ["No se recibieron símbolos para get_ohlcv intradía."], {
            "ohlcv_intraday_requested": 0,
            "ohlcv_intraday_available": 0,
            "ohlcv_vwap_available": 0,
        }

    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    available = 0
    vwap_available = 0

    for tv_symbol in normalized:
        short = tv_symbol.split(":", 1)[-1].upper()
        try:
            history, ohlcv_warnings = fetch_ohlcv(tv_symbol, interval=interval, count=count)
            warnings.extend([f"{tv_symbol}: {warning}" for warning in ohlcv_warnings])
        except Exception as exc:
            warnings.append(f"get_ohlcv intradía falló para {tv_symbol}: {exc}")
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                warnings.append("rate limit alcanzado en get_ohlcv intradía; se detuvieron consultas adicionales")
                break
            continue

        if history.empty:
            warnings.append(f"get_ohlcv intradía sin barras parseables para {tv_symbol}.")
            continue

        required = ["High", "Low", "Close"]
        if any(col not in history.columns for col in required):
            warnings.append(
                f"get_ohlcv intradía sin columnas HLC completas para {tv_symbol}. columnas={list(history.columns)}"
            )
            continue

        bars = history.dropna(subset=required).copy()
        if bars.empty:
            warnings.append(f"get_ohlcv intradía sin barras HLC válidas para {tv_symbol}.")
            continue

        for col in ["High", "Low", "Close", "Volume"]:
            if col in bars.columns:
                bars[col] = pd.to_numeric(bars[col], errors="coerce")
        bars = bars.dropna(subset=required)
        if bars.empty:
            warnings.append(f"get_ohlcv intradía sin números HLC válidos para {tv_symbol}.")
            continue

        intraday_high = _safe_float(bars["High"].max())
        intraday_low = _safe_float(bars["Low"].min())
        last_close = _safe_float(bars["Close"].iloc[-1])
        if intraday_high is None or intraday_low is None or last_close in (None, 0):
            warnings.append(f"get_ohlcv intradía sin high/low/close útiles para {tv_symbol}.")
            continue

        volume = bars["Volume"] if "Volume" in bars.columns else pd.Series([0] * len(bars))
        volume = pd.to_numeric(volume, errors="coerce").fillna(0)
        intraday_volume_sum = _safe_float(volume.sum()) or 0.0

        vwap = None
        if intraday_volume_sum > 0:
            typical_price = (bars["High"] + bars["Low"] + bars["Close"]) / 3
            vwap = _safe_float((typical_price * volume).sum() / intraday_volume_sum)

        recent_lows = bars["Low"].tail(min(20, len(bars))).dropna()
        support = _safe_float(recent_lows.min()) if not recent_lows.empty else intraday_low
        previous_high = _safe_float(bars["High"].iloc[:-1].max()) if len(bars) > 1 else None
        broke_intraday_high = (last_close > previous_high) if previous_high is not None else None

        levels = {
            "intraday_high": round(intraday_high, 4),
            "intraday_low": round(intraday_low, 4),
            "intraday_range_pct": round(((intraday_high - intraday_low) / last_close) * 100, 4),
            "last_close_intraday": round(last_close, 4),
            "intraday_volume_sum": round(intraday_volume_sum, 4),
            "approx_intraday_vwap_from_bars": round(vwap, 4) if vwap is not None else None,
            "distance_to_vwap_pct": round(((last_close - vwap) / vwap) * 100, 4) if vwap not in (None, 0) else None,
            "near_intraday_high": ((intraday_high - last_close) / intraday_high) <= 0.005 if intraday_high else False,
            "near_intraday_low": ((last_close - intraday_low) / intraday_low) <= 0.005 if intraday_low else False,
            "broke_intraday_high": broke_intraday_high,
            "support_intraday": round(support, 4) if support is not None else round(intraday_low, 4),
            "resistance_intraday": round(intraday_high, 4),
            "ohlcv_interval": interval,
            "ohlcv_bars_count": int(len(bars)),
        }
        records[tv_symbol.upper()] = levels
        records[short] = levels
        available += 1
        if vwap is not None:
            vwap_available += 1

    diagnostics = {
        "ohlcv_intraday_requested": len(normalized),
        "ohlcv_intraday_available": available,
        "ohlcv_vwap_available": vwap_available,
    }
    return records, warnings, diagnostics

def fetch_tvremix_data(
    symbol: str,
    use_intraday: bool = True,
    use_ohlcv_levels: bool = True,
    ohlcv_interval: str = "5m",
) -> MarketDataResult:
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

    intraday_data: dict[str, Any] = {}
    intraday_levels: dict[str, Any] = {}
    intraday_enabled = bool(use_intraday)
    ohlcv_levels_enabled = bool(use_intraday and use_ohlcv_levels)

    if intraday_enabled:
        symbol_intraday_map, symbol_intraday_warnings, _ = fetch_intraday_symbol_data_batch([tv_symbol])
        warnings.extend(symbol_intraday_warnings)
        intraday_data = symbol_intraday_map.get(tv_symbol.upper()) or symbol_intraday_map.get(user_symbol, {})
    else:
        warnings.append("capa intradía omitida por --skip-intraday")

    qqq_change_percent = None
    if intraday_enabled:
        try:
            qqq_map, qqq_warnings = fetch_quotes_batch(["QQQ"])
            warnings.extend(qqq_warnings)
            qqq_quote = qqq_map.get("QQQ") or qqq_map.get("NASDAQ:QQQ") or {}
            qqq_change_percent = qqq_quote.get("change_percent")
            if qqq_change_percent in (None, ""):
                qqq_change_percent = qqq_quote.get("change")
            qqq_change_percent = float(qqq_change_percent) if qqq_change_percent not in (None, "") else None
        except Exception:
            qqq_change_percent = None
        if qqq_change_percent is None:
            warnings.append("QQQ no disponible; RS vs QQQ = N/A")

    if ohlcv_levels_enabled:
        ohlcv_levels_map, ohlcv_level_warnings, _ = fetch_intraday_ohlcv_levels([tv_symbol], interval=ohlcv_interval)
        warnings.extend(ohlcv_level_warnings)
        intraday_levels = ohlcv_levels_map.get(tv_symbol.upper()) or ohlcv_levels_map.get(user_symbol, {})
    elif intraday_enabled:
        warnings.append("niveles OHLCV omitidos por --skip-ohlcv-levels")

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
        "rvol_10d": intraday_data.get("rvol_10d"),
        "vwap": intraday_data.get("vwap"),
        "premarket_change": intraday_data.get("premarket_change"),
        "premarket_gap": intraday_data.get("premarket_gap"),
        "premarket_high": intraday_data.get("premarket_high"),
        "premarket_low": intraday_data.get("premarket_low"),
        "gap": intraday_data.get("gap"),
        "intraday_close": intraday_data.get("intraday_close"),
        "intraday_volume": intraday_data.get("intraday_volume"),
        "qqq_change_percent": qqq_change_percent,
        "relative_strength_vs_qqq": None,
        "intraday_high": intraday_levels.get("intraday_high"),
        "intraday_low": intraday_levels.get("intraday_low"),
        "last_close_intraday": intraday_levels.get("last_close_intraday"),
        "approx_intraday_vwap_from_bars": intraday_levels.get("approx_intraday_vwap_from_bars"),
        "distance_to_vwap_pct": intraday_levels.get("distance_to_vwap_pct"),
        "intraday_range_pct": intraday_levels.get("intraday_range_pct"),
        "support_intraday": intraday_levels.get("support_intraday"),
        "resistance_intraday": intraday_levels.get("resistance_intraday"),
        "near_intraday_high": intraday_levels.get("near_intraday_high"),
        "near_intraday_low": intraday_levels.get("near_intraday_low"),
        "intraday_enabled": intraday_enabled,
        "ohlcv_levels_enabled": ohlcv_levels_enabled,
    }

    symbol_change = market_data.get("change_percent")
    if symbol_change in (None, ""):
        symbol_change = intraday_data.get("intraday_change")
    try:
        symbol_change_num = float(symbol_change) if symbol_change not in (None, "") else None
    except (TypeError, ValueError):
        symbol_change_num = None
    if qqq_change_percent is not None and symbol_change_num is not None:
        market_data["relative_strength_vs_qqq"] = round(symbol_change_num - qqq_change_percent, 4)

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
