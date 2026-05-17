from __future__ import annotations

from src.data_sources.nasdaq100 import load_nasdaq100_symbols
from src.data_sources.tvremix_client import (
    fetch_earnings_calendar,
    fetch_news_for_symbols,
    fetch_quotes_batch,
    fetch_technicals_batch,
)
from src.scoring.scanner_score import score_candidate


def _extract_quote_core(quote: dict) -> dict:
    data = quote.get("data") if isinstance(quote.get("data"), dict) else quote
    return data if isinstance(data, dict) else {}


def _first_non_empty(item: dict, keys: list[str]):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def scan_nasdaq100(source: str = "tvremix", limit: int = 10) -> list[dict]:
    if source.strip().lower() != "tvremix":
        raise ValueError("Por ahora scan-nasdaq100 solo soporta --source tvremix")

    symbols = load_nasdaq100_symbols()
    selected = symbols[: max(1, int(limit))]

    quotes_map, quote_warnings = fetch_quotes_batch(selected)
    technicals_map, tech_warnings = fetch_technicals_batch(selected)
    news_map, news_warnings = fetch_news_for_symbols(selected, limit_per_symbol=3)
    earnings_map, earnings_warnings = fetch_earnings_calendar(selected)

    candidates: list[dict] = []
    for symbol in selected:
        key = symbol.upper()
        quote_raw = quotes_map.get(key, {})
        tech_raw = technicals_map.get(key, {})
        news_items = news_map.get(key, [])
        earnings_items = earnings_map.get(key, [])

        quote = _extract_quote_core(quote_raw)
        tech_data = tech_raw.get("data") if isinstance(tech_raw.get("data"), dict) else tech_raw
        summary = tech_data.get("summary", {}) if isinstance(tech_data, dict) else {}
        oscillators = tech_data.get("oscillators", {}) if isinstance(tech_data, dict) else {}

        latest_titles = [
            _first_non_empty(item, ["title", "headline", "name", "text"])
            for item in news_items
            if isinstance(item, dict)
        ]
        latest_titles = [str(x) for x in latest_titles if x][:3]

        earnings_nearby = bool(earnings_items)
        catalyst_summary = "Sin catalizador confirmado"
        has_recent_catalyst = False
        if latest_titles:
            has_recent_catalyst = True
            catalyst_summary = f"{len(latest_titles)} titulares recientes"
        if earnings_nearby:
            has_recent_catalyst = True
            catalyst_summary = (catalyst_summary + " + earnings cercano") if latest_titles else "Earnings cercano"

        candidate = {
            "ticker": symbol,
            "price": quote.get("price") or quote.get("last_price") or quote.get("close"),
            "change_percent": quote.get("change_percent"),
            "volume": quote.get("volume"),
            "market_cap": quote.get("market_cap"),
            "pe_ratio": quote.get("pe_ratio"),
            "technical_rating": summary.get("recommendation") or tech_data.get("recommendation"),
            "rsi": oscillators.get("rsi") or tech_data.get("rsi"),
            "latest_news_titles": latest_titles,
            "news_count": len(latest_titles),
            "catalyst_summary": catalyst_summary,
            "has_recent_catalyst": has_recent_catalyst,
            "earnings_nearby": earnings_nearby,
            "earnings_items": earnings_items,
            "catalyst_warnings": [],
            "warnings": [],
        }

        cp = candidate.get("change_percent")
        if cp not in (None, ""):
            try:
                cp = float(cp)
                if cp >= 4 and not has_recent_catalyst:
                    candidate["catalyst_warnings"].append("Movimiento sin catalizador confirmado")
                if cp <= -4 and not has_recent_catalyst:
                    candidate["catalyst_warnings"].append("Caída fuerte sin noticia confirmada")
            except (TypeError, ValueError):
                pass

        missing = [k for k in ["price", "change_percent", "volume", "technical_rating", "rsi"] if candidate.get(k) in (None, "")]
        candidate["missing_fields"] = missing
        if key not in quotes_map:
            candidate["warnings"].append("quote no disponible en get_quotes_batch")
        if key not in technicals_map:
            candidate["warnings"].append("technicals no disponibles en get_technicals")

        candidate["warnings"].extend(candidate["catalyst_warnings"])
        candidate.update(score_candidate(candidate))
        candidates.append(candidate)

    shared_warnings = quote_warnings + tech_warnings + news_warnings + earnings_warnings
    if shared_warnings:
        for candidate in candidates:
            candidate["warnings"].extend(shared_warnings)

    return sorted(candidates, key=lambda c: c.get("total_score", 0), reverse=True)
