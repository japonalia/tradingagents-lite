from __future__ import annotations

from src.data_sources.nasdaq100 import load_nasdaq100_symbols
from src.data_sources.tvremix_client import fetch_quotes_batch, fetch_technicals_batch
from src.scoring.scanner_score import score_candidate


def _extract_quote_core(quote: dict) -> dict:
    data = quote.get("data") if isinstance(quote.get("data"), dict) else quote
    return data if isinstance(data, dict) else {}


def scan_nasdaq100(source: str = "tvremix", limit: int = 10) -> list[dict]:
    if source.strip().lower() != "tvremix":
        raise ValueError("Por ahora scan-nasdaq100 solo soporta --source tvremix")

    symbols = load_nasdaq100_symbols()
    selected = symbols[: max(1, int(limit))]

    quotes_map, quote_warnings = fetch_quotes_batch(selected)
    technicals_map, tech_warnings = fetch_technicals_batch(selected)

    candidates: list[dict] = []
    for symbol in selected:
        key = symbol.upper()
        quote_raw = quotes_map.get(key, {})
        tech_raw = technicals_map.get(key, {})

        quote = _extract_quote_core(quote_raw)
        tech_data = tech_raw.get("data") if isinstance(tech_raw.get("data"), dict) else tech_raw
        summary = tech_data.get("summary", {}) if isinstance(tech_data, dict) else {}
        oscillators = tech_data.get("oscillators", {}) if isinstance(tech_data, dict) else {}

        candidate = {
            "ticker": symbol,
            "price": quote.get("price") or quote.get("last_price") or quote.get("close"),
            "change_percent": quote.get("change_percent"),
            "volume": quote.get("volume"),
            "market_cap": quote.get("market_cap"),
            "pe_ratio": quote.get("pe_ratio"),
            "technical_rating": summary.get("recommendation") or tech_data.get("recommendation"),
            "rsi": oscillators.get("rsi") or tech_data.get("rsi"),
            "warnings": [],
        }

        missing = [k for k in ["price", "change_percent", "volume", "technical_rating", "rsi"] if candidate.get(k) in (None, "")]
        candidate["missing_fields"] = missing
        if key not in quotes_map:
            candidate["warnings"].append("quote no disponible en get_quotes_batch")
        if key not in technicals_map:
            candidate["warnings"].append("technicals no disponibles en get_technicals")

        candidate.update(score_candidate(candidate))
        candidates.append(candidate)

    shared_warnings = quote_warnings + tech_warnings
    if shared_warnings:
        for candidate in candidates:
            candidate["warnings"].extend(shared_warnings)

    return sorted(candidates, key=lambda c: c.get("total_score", 0), reverse=True)
