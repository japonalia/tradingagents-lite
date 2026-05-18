from __future__ import annotations

from src.data_sources.nasdaq100 import load_nasdaq100_symbols
from src.data_sources.tvremix_client import (
    fetch_earnings_calendar,
    fetch_multi_timeframe_technicals_batch,
    fetch_news_for_symbols,
    fetch_quotes_batch,
    fetch_technicals,
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


def scan_nasdaq100(source: str = "tvremix", limit: int = 10, catalyst_top_n: int = 10, technical_top_n: int = 25, max_symbols: int | None = None) -> dict:
    if source.strip().lower() != "tvremix":
        raise ValueError("Por ahora scan-nasdaq100 solo soporta --source tvremix")

    symbols = load_nasdaq100_symbols()
    universe_symbols = symbols
    if max_symbols is not None:
        universe_symbols = symbols[: max(1, int(max_symbols))]
    global_warnings: list[str] = []

    quotes_map, quote_warnings = fetch_quotes_batch(universe_symbols)
    global_warnings.extend(quote_warnings)

    candidates: list[dict] = []
    for symbol in universe_symbols:
        key = symbol.upper()
        quote_raw = quotes_map.get(key, {})
        quote = _extract_quote_core(quote_raw)

        latest_titles = []
        earnings_nearby = False
        earnings_items = []
        catalyst_summary = "Sin catalizador confirmado"
        has_recent_catalyst = False

        candidate = {
            "ticker": symbol,
            "price": quote.get("price") or quote.get("last_price") or quote.get("close"),
            "change_percent": quote.get("change_percent"),
            "volume": quote.get("volume"),
            "market_cap": quote.get("market_cap"),
            "pe_ratio": quote.get("pe_ratio"),
            "technical_rating": None,
            "rsi": None,
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

        candidate["warnings"].extend(candidate["catalyst_warnings"])
        candidate.update(score_candidate(candidate))
        candidate["preliminary_score"] = candidate.get("total_score", 0)
        candidates.append(candidate)

    ranked = sorted(candidates, key=lambda c: c.get("preliminary_score", 0), reverse=True)
    technical_n = max(1, int(technical_top_n))
    technical_symbols = [c["ticker"] for c in ranked[:technical_n]]
    technical_symbol_keys = {x.upper() for x in technical_symbols}
    technicals_map: dict = {}
    technical_fallback_count = 0

    try:
        technicals_map, tech_warnings = fetch_multi_timeframe_technicals_batch(
            technical_symbols, timeframes=["1D"]
        )
        global_warnings.extend(tech_warnings)
    except Exception as exc:
        global_warnings.append(f"analyze_multi_timeframe_batch falló globalmente: {exc}")

    if technical_symbols:
        fallback_candidates = []
        for symbol in technical_symbols:
            tv_symbol = f"NASDAQ:{symbol.upper()}" if ":" not in symbol else symbol.upper()
            short = tv_symbol.split(":", 1)[-1].upper()
            tech_item = technicals_map.get(tv_symbol) or technicals_map.get(short) or {}
            if not isinstance(tech_item, dict) or not any(
                tech_item.get(k) not in (None, "")
                for k in ("technical_rating", "technical_rating_value", "rsi", "macd", "summary_markdown")
            ):
                fallback_candidates.append(tv_symbol)

        fallback_limit = min(5, len(fallback_candidates))
        if fallback_candidates and fallback_limit < len(fallback_candidates):
            global_warnings.append(
                f"fallback técnicos individuales limitado a {fallback_limit}/{len(fallback_candidates)} símbolos para evitar rate limit"
            )

        rate_limit_stopped = False
        rate_limit_warning_added = False
        for tv_symbol in fallback_candidates[:fallback_limit]:
            if rate_limit_stopped:
                break
            short = tv_symbol.split(":", 1)[-1].upper()
            try:
                technicals, tech_warnings = fetch_technicals(tv_symbol, interval="1D")
                global_warnings.extend(tech_warnings)
                technicals_map[tv_symbol] = technicals
                technicals_map[short] = technicals
                technical_fallback_count += 1
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "Too Many Requests" in msg:
                    rate_limit_stopped = True
                    if not rate_limit_warning_added:
                        global_warnings.append(
                            "rate limit alcanzado en técnicos; se detuvieron consultas adicionales"
                        )
                        rate_limit_warning_added = True
                else:
                    global_warnings.append(f"get_technicals falló para {tv_symbol}: {exc}")

    for candidate in candidates:
        key = candidate["ticker"].upper()
        if key not in technical_symbol_keys:
            candidate["warnings"].append("technicals omitidos fuera de technical_top_n")
            candidate.update(score_candidate(candidate))
            continue
        tech_raw = technicals_map.get(key, {})
        tech_data = tech_raw.get("data") if isinstance(tech_raw, dict) and isinstance(tech_raw.get("data"), dict) else tech_raw
        candidate["technical_batch_summary"] = tech_data.get("summary_markdown") if isinstance(tech_data, dict) else None
        summary = tech_data.get("summary", {}) if isinstance(tech_data, dict) else {}
        oscillators = tech_data.get("oscillators", {}) if isinstance(tech_data, dict) else {}
        candidate["technical_rating"] = (
            candidate.get("technical_rating")
            or (tech_data.get("technical_rating") if isinstance(tech_data, dict) else None)
            or summary.get("recommendation")
            or (tech_data.get("recommendation") if isinstance(tech_data, dict) else None)
        )
        candidate["rsi"] = (
            candidate.get("rsi")
            or (tech_data.get("rsi") if isinstance(tech_data, dict) else None)
            or oscillators.get("rsi")
        )
        if not candidate.get("technical_rating") and not candidate.get("rsi"):
            candidate["warnings"].append("technicals no disponibles en analyze_multi_timeframe_batch/get_technicals")
        candidate["missing_fields"] = [k for k in ["price", "change_percent", "volume", "technical_rating", "rsi"] if candidate.get(k) in (None, "")]
        candidate.update(score_candidate(candidate))

    top_n = max(1, int(catalyst_top_n))
    catalyst_symbols = [c["ticker"] for c in ranked[:top_n]]
    catalyst_symbol_keys = {x.upper() for x in catalyst_symbols}

    news_map: dict = {}
    earnings_map: dict = {}
    rate_limit_reached = False
    earnings_rate_limit_reached = False

    try:
        news_map, news_warnings = fetch_news_for_symbols(catalyst_symbols, limit_per_symbol=3)
        global_warnings.extend(news_warnings)
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "Too Many Requests" in msg:
            rate_limit_reached = True
            global_warnings.append("rate limit alcanzado: se omiten noticias/earnings restantes")
        else:
            global_warnings.append(f"get_news fallo global: {exc}")

    if not rate_limit_reached:
        try:
            earnings_map, earnings_warnings = fetch_earnings_calendar(catalyst_symbols)
            global_warnings.extend(earnings_warnings)
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too Many Requests" in msg:
                rate_limit_reached = True
                earnings_rate_limit_reached = True
            else:
                global_warnings.append(f"get_earnings_calendar fallo global: {exc}")

    for candidate in candidates:
        key = candidate["ticker"].upper()
        if key not in catalyst_symbol_keys:
            candidate.update(score_candidate(candidate))
            continue

        news_items = news_map.get(key, [])
        earnings_items = earnings_map.get(key, [])
        latest_titles = [
            _first_non_empty(item, ["title", "headline", "name", "text"])
            for item in news_items
            if isinstance(item, dict)
        ]
        latest_titles = [str(x) for x in latest_titles if x][:3]
        earnings_nearby = bool(earnings_items)
        has_recent_catalyst = bool(latest_titles or earnings_nearby)
        if latest_titles and earnings_nearby:
            catalyst_summary = f"{len(latest_titles)} titulares recientes + earnings cercano"
        elif latest_titles:
            catalyst_summary = f"{len(latest_titles)} titulares recientes"
        elif earnings_nearby:
            catalyst_summary = "Earnings cercano"
        else:
            catalyst_summary = "Sin catalizador confirmado"

        candidate["latest_news_titles"] = latest_titles
        candidate["news_count"] = len(latest_titles)
        candidate["earnings_items"] = earnings_items
        candidate["earnings_nearby"] = earnings_nearby
        candidate["has_recent_catalyst"] = has_recent_catalyst
        candidate["catalyst_summary"] = catalyst_summary
        candidate.update(score_candidate(candidate))

    no_headlines_symbols = 0
    for candidate in candidates:
        if candidate["ticker"].upper() in catalyst_symbol_keys and not candidate.get("latest_news_titles"):
            no_headlines_symbols += 1

    if no_headlines_symbols:
        global_warnings.append(f"get_news sin titulares parseables para {no_headlines_symbols} símbolos")

    if earnings_rate_limit_reached:
        global_warnings.append("rate limit alcanzado en earnings; se detuvieron consultas adicionales")

    deduped_global_warnings = []
    seen = set()
    for warning in global_warnings:
        key = warning.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_global_warnings.append(key)

    ranked_final = sorted(candidates, key=lambda c: c.get("total_score", 0), reverse=True)
    shown_limit = max(1, int(limit))

    technical_batch_available = sum(
        1 for c in candidates if c.get("ticker", "").upper() in technical_symbol_keys and (c.get("technical_rating") not in (None, "") or c.get("rsi") not in (None, ""))
    )
    technical_unavailable = max(len(technical_symbols) - technical_batch_available, 0)

    return {
        "symbols_in_universe": len(symbols),
        "candidates_evaluated": len(candidates),
        "candidates_shown": min(shown_limit, len(ranked_final)),
        "quotes_available": sum(1 for c in candidates if c.get("price") not in (None, "")),
        "technicals_available": sum(1 for c in candidates if c.get("technical_rating") not in (None, "") or c.get("rsi") not in (None, "")),
        "technicals_batch_available": technical_batch_available,
        "technicals_fallback_individual": technical_fallback_count,
        "technicals_not_available": technical_unavailable,
        "catalysts_queried": len(catalyst_symbols),
        "candidates": ranked_final[:shown_limit],
        "global_warnings": deduped_global_warnings,
    }
