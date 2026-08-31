from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.audit.scanner_audit import build_scanner_audit
from src.catalysts.premarket_engine import evaluate_premarket_catalysts
from src.data_sources.catalysts import fetch_external_catalysts
from src.data_sources.nasdaq100 import load_nasdaq100_symbols
from src.data_quality.provenance import build_field_provenance
from src.data_sources.tvremix_client import (
    fetch_earnings_calendar,
    fetch_intraday_ohlcv_levels,
    fetch_intraday_screener_fields,
    fetch_intraday_symbol_data_batch,
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


def _dedup_messages(values: list[str] | None) -> list[str]:
    seen = set()
    out: list[str] = []
    for value in values or []:
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _observation_timestamp(item: dict) -> object:
    return _first_non_empty(item, ["timestamp", "datetime", "time", "date", "updated_at", "as_of"])


def _quality_hint(item: dict) -> object:
    return _first_non_empty(item, ["quality_state", "data_quality", "quality", "status"])


def _rank_candidates(candidates: list[dict], score_field: str = "total_score") -> list[dict]:
    def key(candidate: dict) -> tuple[float, str]:
        try:
            score = float(candidate.get(score_field, 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        return (-score, str(candidate.get("ticker") or ""))

    return sorted(candidates, key=key)


def scan_nasdaq100(source: str = "tvremix", limit: int = 10, catalyst_top_n: int = 10, technical_top_n: int = 25, intraday_top_n: int = 10, ohlcv_top_n: int = 5, ohlcv_interval: str = "5m", max_symbols: int | None = None, skip_news: bool = False, skip_earnings: bool = True, use_intraday: bool = True, use_ohlcv_levels: bool = True, use_external_catalysts: bool = False, catalyst_scope: str = "universe") -> dict:
    if source.strip().lower() != "tvremix":
        raise ValueError("Por ahora scan-nasdaq100 solo soporta --source tvremix")
    normalized_catalyst_scope = catalyst_scope.strip().lower()
    if normalized_catalyst_scope not in {"universe", "top"}:
        raise ValueError("catalyst_scope debe ser 'universe' o 'top'")

    run_started_at = datetime.now(timezone.utc)
    run_id = str(uuid4())

    symbols = load_nasdaq100_symbols()
    universe_symbols = symbols
    if max_symbols is not None:
        universe_symbols = symbols[: max(1, int(max_symbols))]
    global_warnings: list[str] = []

    quotes_map, quote_warnings = fetch_quotes_batch(universe_symbols)
    global_warnings.extend(quote_warnings)

    qqq_quote_map, qqq_quote_warnings = fetch_quotes_batch(["QQQ"])
    global_warnings.extend(qqq_quote_warnings)
    qqq_quote = _extract_quote_core(qqq_quote_map.get("QQQ", {}))
    qqq_change_percent = qqq_quote.get("change_percent")
    if qqq_change_percent in (None, ""):
        qqq_change_percent = qqq_quote.get("change")
    try:
        qqq_change_percent = float(qqq_change_percent) if qqq_change_percent not in (None, "") else None
    except (TypeError, ValueError):
        qqq_change_percent = None
    if qqq_change_percent is None:
        global_warnings.append("QQQ no disponible; fuerza relativa no calculada")
    intraday_map: dict[str, dict] = {}
    intraday_diagnostics: dict = {}
    intraday_source_counts = {"run_screener": 0, "get_symbol_data": 0}
    if use_intraday:
        intraday_map, intraday_warnings, intraday_diagnostics = fetch_intraday_screener_fields(
            universe_symbols
        )
        global_warnings.extend(intraday_warnings)
        intraday_source_counts["run_screener"] = int(intraday_diagnostics.get("screener_symbols_matched", 0))

    candidates: list[dict] = []
    for symbol in universe_symbols:
        key = symbol.upper()
        quote_raw = quotes_map.get(key, {})
        quote = _extract_quote_core(quote_raw)
        intraday_raw = intraday_map.get(key) or intraday_map.get(f"NASDAQ:{key}") or {}

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
            "market_cap": quote.get("market_cap") or intraday_raw.get("market_cap_basic"),
            "pe_ratio": quote.get("pe_ratio") or intraday_raw.get("price_earnings_ttm"),
            "intraday_close": intraday_raw.get("intraday_close", intraday_raw.get("close")),
            "intraday_change": intraday_raw.get("intraday_change", intraday_raw.get("change")),
            "intraday_change_abs": intraday_raw.get("intraday_change_abs", intraday_raw.get("change_abs")),
            "intraday_volume": intraday_raw.get("intraday_volume", intraday_raw.get("volume")),
            "avg_volume_10d": intraday_raw.get("avg_volume_10d", intraday_raw.get("average_volume_10d_calc")),
            "rvol_10d": intraday_raw.get("rvol_10d", intraday_raw.get("relative_volume_10d_calc")),
            "vwap": intraday_raw.get("vwap", intraday_raw.get("VWAP")),
            "premarket_change": intraday_raw.get("premarket_change"),
            "premarket_gap": intraday_raw.get("premarket_gap"),
            "premarket_high": intraday_raw.get("premarket_high"),
            "premarket_low": intraday_raw.get("premarket_low"),
            "gap": intraday_raw.get("gap"),
            "days_to_earnings": intraday_raw.get("days_to_earnings"),
            "price_vs_ema50_pct": intraday_raw.get("price_vs_ema50_pct"),
            "price_vs_ema200_pct": intraday_raw.get("price_vs_ema200_pct"),
            "technical_rating": None,
            "rsi": None,
            "latest_news_titles": latest_titles,
            "news_count": len(latest_titles),
            "catalyst_summary": catalyst_summary,
            "has_recent_catalyst": has_recent_catalyst,
            "earnings_nearby": earnings_nearby,
            "earnings_items": earnings_items,
            "catalyst_headlines": [],
            "catalyst_source_count": 0,
            "catalyst_score": 0.0,
            "catalyst_ranking_credit": 0.0,
            "catalyst_classification": "NOISE",
            "catalyst_validation_state": "unverified",
            "catalyst_warnings": [],
            "warnings": [],
            "technical_source": None,
            "qqq_change_percent": qqq_change_percent,
            "relative_strength_vs_qqq": None,
            "use_intraday": use_intraday,
            "intraday_expected": use_intraday,
        }

        quote_observed = _observation_timestamp(quote)
        quote_quality = _quality_hint(quote)
        intraday_observed = _observation_timestamp(intraday_raw)
        intraday_quality = _quality_hint(intraday_raw)
        candidate["data_provenance"] = {}
        for field in ("price", "change_percent", "volume"):
            candidate["data_provenance"][field] = build_field_provenance(
                field=field,
                value=candidate.get(field),
                source="tvremix:get_quotes_batch",
                observed_at=quote_observed,
                received_at=run_started_at,
                quality_hint=quote_quality,
            )
        for field in ("intraday_close", "intraday_change", "intraday_volume", "rvol_10d", "vwap", "premarket_change", "premarket_gap"):
            candidate["data_provenance"][field] = build_field_provenance(
                field=field,
                value=candidate.get(field),
                source="tvremix:run_screener",
                observed_at=intraday_observed,
                received_at=run_started_at,
                quality_hint=intraday_quality,
            )
        if candidate.get("price") in (None, "") and candidate.get("intraday_close") not in (None, ""):
            candidate["price"] = candidate["intraday_close"]
        if candidate.get("volume") in (None, "") and candidate.get("intraday_volume") not in (None, ""):
            candidate["volume"] = candidate["intraday_volume"]
        if candidate.get("change_percent") in (None, "") and candidate.get("intraday_change") not in (None, ""):
            candidate["change_percent"] = candidate["intraday_change"]
        fallback_fields = {
            "price": candidate.get("price"),
            "volume": candidate.get("volume"),
            "change_percent": candidate.get("change_percent"),
        }
        for field, field_value in fallback_fields.items():
            if candidate["data_provenance"][field]["quality_state"] == "unavailable" and field_value not in (None, ""):
                candidate["data_provenance"][field] = build_field_provenance(
                    field=field,
                    value=field_value,
                    source="tvremix:run_screener",
                    observed_at=intraday_observed,
                    received_at=run_started_at,
                    quality_hint=intraday_quality,
                )

        candidate_change_percent = candidate.get("intraday_change")
        if candidate_change_percent in (None, ""):
            candidate_change_percent = candidate.get("change_percent")
        try:
            candidate_change_percent = float(candidate_change_percent) if candidate_change_percent not in (None, "") else None
        except (TypeError, ValueError):
            candidate_change_percent = None
        if qqq_change_percent is not None and candidate_change_percent is not None:
            candidate["relative_strength_vs_qqq"] = round(candidate_change_percent - qqq_change_percent, 4)

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
        candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
        candidate["reasons"] = _dedup_messages(candidate.get("reasons"))
        candidate["preliminary_score"] = candidate.get("total_score", 0)
        candidates.append(candidate)

    ranked = _rank_candidates(candidates, "preliminary_score")
    if use_intraday:
        matched = int(intraday_diagnostics.get("screener_symbols_matched", 0))
        if matched < 5:
            intraday_n = max(1, int(intraday_top_n))
            fallback_intraday_symbols = [c["ticker"] for c in ranked[:intraday_n]]
            global_warnings.append(
                f"run_screener sin cobertura útil; usando get_symbol_data para Top {len(fallback_intraday_symbols)}"
            )
            symbol_data_map, symbol_data_warnings, symbol_data_diag = fetch_intraday_symbol_data_batch(
                fallback_intraday_symbols
            )
            global_warnings.extend(symbol_data_warnings)
            intraday_source_counts["get_symbol_data"] = int(symbol_data_diag.get("symbol_data_success", 0))
            intraday_map.update(symbol_data_map)
            for candidate in candidates:
                key = candidate["ticker"].upper()
                intraday_raw = intraday_map.get(key) or intraday_map.get(f"NASDAQ:{key}") or {}
                if not intraday_raw:
                    continue
                candidate["intraday_close"] = candidate.get("intraday_close") or intraday_raw.get("intraday_close", intraday_raw.get("close"))
                candidate["intraday_change"] = candidate.get("intraday_change") or intraday_raw.get("intraday_change", intraday_raw.get("change"))
                candidate["intraday_change_abs"] = candidate.get("intraday_change_abs") or intraday_raw.get("intraday_change_abs", intraday_raw.get("change_abs"))
                candidate["intraday_volume"] = candidate.get("intraday_volume") or intraday_raw.get("intraday_volume", intraday_raw.get("volume"))
                candidate["avg_volume_10d"] = candidate.get("avg_volume_10d") or intraday_raw.get("avg_volume_10d", intraday_raw.get("average_volume_10d_calc"))
                candidate["rvol_10d"] = candidate.get("rvol_10d") or intraday_raw.get("rvol_10d", intraday_raw.get("relative_volume_10d_calc"))
                candidate["vwap"] = candidate.get("vwap") or intraday_raw.get("vwap", intraday_raw.get("VWAP"))
                candidate["premarket_change"] = candidate.get("premarket_change") or intraday_raw.get("premarket_change")
                candidate["premarket_gap"] = candidate.get("premarket_gap") or intraday_raw.get("premarket_gap")
                candidate["premarket_high"] = candidate.get("premarket_high") or intraday_raw.get("premarket_high")
                candidate["premarket_low"] = candidate.get("premarket_low") or intraday_raw.get("premarket_low")
                candidate["gap"] = candidate.get("gap") or intraday_raw.get("gap")
                fallback_observed = _observation_timestamp(intraday_raw)
                fallback_quality = _quality_hint(intraday_raw)
                fallback_keys = {
                    "intraday_close": ("intraday_close", "close"),
                    "intraday_change": ("intraday_change", "change"),
                    "intraday_volume": ("intraday_volume", "volume"),
                    "rvol_10d": ("rvol_10d", "relative_volume_10d_calc"),
                    "vwap": ("vwap", "VWAP"),
                    "premarket_change": ("premarket_change",),
                    "premarket_gap": ("premarket_gap",),
                }
                for field, raw_keys in fallback_keys.items():
                    fallback_value = _first_non_empty(intraday_raw, list(raw_keys))
                    previous = candidate["data_provenance"].get(field, {})
                    if fallback_value not in (None, "") and previous.get("quality_state") == "unavailable":
                        candidate["data_provenance"][field] = build_field_provenance(
                            field=field,
                            value=fallback_value,
                            source="tvremix:get_symbol_data",
                            observed_at=fallback_observed,
                            received_at=run_started_at,
                            quality_hint=fallback_quality,
                        )

    ohlcv_levels_map: dict[str, dict] = {}
    ohlcv_level_symbols: list[str] = []
    ohlcv_level_diag = {
        "ohlcv_intraday_requested": 0,
        "ohlcv_intraday_available": 0,
        "ohlcv_vwap_available": 0,
    }
    ohlcv_visible_in_top = 0
    if not use_ohlcv_levels:
        global_warnings.append("niveles intradía OHLCV omitidos por --skip-ohlcv-levels")

    ranked = _rank_candidates(candidates)

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
            candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
            candidate["reasons"] = _dedup_messages(candidate.get("reasons"))
            continue
        tech_raw = technicals_map.get(key, {})
        tech_data = tech_raw.get("data") if isinstance(tech_raw, dict) and isinstance(tech_raw.get("data"), dict) else tech_raw
        candidate["technical_batch_summary"] = tech_data.get("summary_markdown") if isinstance(tech_data, dict) else None
        if isinstance(tech_data, dict):
            candidate["technical_rating"] = candidate.get("technical_rating") or tech_data.get("technical_rating")
            candidate["technical_rating_value"] = tech_data.get("technical_rating_value")
            candidate["rsi"] = candidate.get("rsi") or tech_data.get("rsi")
            candidate["macd"] = tech_data.get("macd")
            candidate["macd_signal"] = tech_data.get("macd_signal")
            candidate["adx"] = tech_data.get("adx")
            candidate["atr"] = tech_data.get("atr")
            candidate["confluence_alignment"] = tech_data.get("confluence_alignment")
            candidate["week_52_high"] = tech_data.get("week_52_high")
            candidate["week_52_low"] = tech_data.get("week_52_low")
            candidate["ma_bias"] = tech_data.get("ma_bias")
            candidate["oscillator_bias"] = tech_data.get("oscillator_bias")
            if candidate.get("price") in (None, ""):
                candidate["price"] = tech_data.get("technical_price")
            if candidate.get("volume") in (None, ""):
                candidate["volume"] = tech_data.get("technical_volume")
            if candidate.get("change_percent") in (None, ""):
                candidate["change_percent"] = tech_data.get("technical_change")
            if candidate.get("technical_rating") not in (None, "") or candidate.get("rsi") not in (None, ""):
                candidate["technical_source"] = "batch"
            technical_observed = _observation_timestamp(tech_data)
            technical_quality = _quality_hint(tech_data)
            for field in ("technical_rating", "rsi", "macd", "adx", "atr"):
                candidate["data_provenance"][field] = build_field_provenance(
                    field=field,
                    value=candidate.get(field),
                    source="tvremix:analyze_multi_timeframe_batch",
                    observed_at=technical_observed,
                    received_at=run_started_at,
                    quality_hint=technical_quality,
                    live_max_age_seconds=86_400,
                    delayed_max_age_seconds=172_800,
                )
        if not candidate.get("technical_rating") and not candidate.get("rsi"):
            candidate["warnings"].append("technicals no disponibles en analyze_multi_timeframe_batch/get_technicals")
        elif candidate.get("technical_source") is None:
            candidate["technical_source"] = "fallback_individual"
        candidate["missing_fields"] = [k for k in ["price", "change_percent", "volume", "technical_rating", "rsi"] if candidate.get(k) in (None, "")]
        candidate.update(score_candidate(candidate))
        candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
        candidate["reasons"] = _dedup_messages(candidate.get("reasons"))

    ranked_pre_catalyst = _rank_candidates(candidates)
    top_n = max(0, int(catalyst_top_n))
    shown_limit = max(1, int(limit))
    ranked_for_catalysts = ranked_pre_catalyst[:shown_limit]
    if top_n <= 0:
        catalyst_symbols = []
    elif normalized_catalyst_scope == "universe":
        catalyst_symbols = [c["ticker"] for c in candidates]
    else:
        catalyst_symbols = [c["ticker"] for c in ranked_for_catalysts[:top_n]]
    catalyst_symbol_keys = {x.upper() for x in catalyst_symbols}

    news_map: dict = {}
    earnings_map: dict = {}
    external_catalysts_map: dict[str, dict] = {}
    external_catalysts_not_configured = False
    rate_limit_reached = False
    earnings_rate_limit_reached = False

    if top_n > 0 and not skip_news:
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

    if top_n > 0 and use_external_catalysts:
        try:
            external_catalysts_map = fetch_external_catalysts(catalyst_symbols, limit_per_symbol=3)
            external_catalysts_not_configured = any(
                "fuente externa de catalizadores no configurada" in (item.get("warnings") or [])
                for item in external_catalysts_map.values()
                if isinstance(item, dict)
            )
        except Exception as exc:
            global_warnings.append(f"external_catalysts fallo global: {exc}")

    if top_n > 0 and not rate_limit_reached and not skip_earnings:
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
            candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
            candidate["reasons"] = _dedup_messages(candidate.get("reasons"))
            continue

        news_items = news_map.get(key, [])
        earnings_items = earnings_map.get(key, [])
        latest_titles = [
            _first_non_empty(item, ["title", "headline", "name", "text"])
            for item in news_items
            if isinstance(item, dict)
        ]
        latest_titles = [str(x) for x in latest_titles if x][:3]
        source_keys = {"provider", "source", "publisher", "channel"}
        source_values = {
            str(item.get(k)).strip()
            for item in news_items
            if isinstance(item, dict)
            for k in source_keys
            if item.get(k) not in (None, "")
        }
        earnings_nearby = bool(earnings_items)

        external_info = external_catalysts_map.get(key, {}) if isinstance(external_catalysts_map, dict) else {}
        candidate["external_catalyst"] = external_info

        catalyst_evaluation = evaluate_premarket_catalysts(
            key,
            news_items=news_items,
            earnings_items=earnings_items,
            market_context={
                "premarket_change": candidate.get("premarket_change"),
                "premarket_gap": candidate.get("premarket_gap"),
                "rvol_10d": candidate.get("rvol_10d"),
            },
            now=run_started_at,
        )
        has_recent_catalyst = bool(catalyst_evaluation.get("confirmed_catalyst"))
        if has_recent_catalyst:
            catalyst_summary = (
                f"{catalyst_evaluation.get('catalyst_classification')} "
                f"({catalyst_evaluation.get('primary_event_type')}, score={catalyst_evaluation.get('catalyst_score')})"
            )
        elif latest_titles or earnings_nearby:
            catalyst_summary = "Evento detectado, pendiente de validación autoritativa"
        else:
            catalyst_summary = "Sin catalizador confirmado"

        candidate["latest_news_titles"] = latest_titles
        candidate["news_count"] = len(latest_titles)
        candidate["earnings_items"] = earnings_items
        candidate["earnings_nearby"] = earnings_nearby
        candidate["has_recent_catalyst"] = has_recent_catalyst
        candidate["catalyst_summary"] = catalyst_summary
        candidate["catalyst_headlines"] = catalyst_evaluation.get("headlines") or latest_titles
        candidate["catalyst_source_count"] = catalyst_evaluation.get("source_count", len(source_values))
        candidate["catalyst_score"] = catalyst_evaluation.get("catalyst_score", 0.0)
        candidate["catalyst_ranking_credit"] = catalyst_evaluation.get("catalyst_ranking_credit", 0.0)
        candidate["catalyst_classification"] = catalyst_evaluation.get("catalyst_classification", "NOISE")
        candidate["catalyst_score_breakdown"] = catalyst_evaluation.get("catalyst_score_breakdown", {})
        candidate["catalyst_validation_state"] = catalyst_evaluation.get("validation_state", "unverified")
        candidate["catalyst_validation_reasons"] = catalyst_evaluation.get("validation_reasons", [])
        candidate["catalyst_direction"] = catalyst_evaluation.get("direction", "neutral")
        candidate["catalyst_events"] = catalyst_evaluation.get("events", [])
        catalyst_events = catalyst_evaluation.get("events") or []
        catalyst_observed_at = catalyst_events[0].get("published_at") if catalyst_events else None
        candidate["data_provenance"]["catalyst"] = build_field_provenance(
            field="catalyst",
            value=candidate.get("catalyst_score") if (latest_titles or earnings_nearby) else None,
            source="tvremix:get_news/get_earnings_calendar",
            observed_at=catalyst_observed_at,
            received_at=run_started_at,
            quality_hint=None,
        )
        if has_recent_catalyst:
            candidate["catalyst_origin"] = "tvremix_get_news"
        elif external_info.get("has_recent_catalyst") and str(external_info.get("validation_state", "")).startswith("confirmed_"):
            candidate["has_recent_catalyst"] = True
            candidate["catalyst_summary"] = external_info.get("catalyst_summary") or candidate["catalyst_summary"]
            candidate["catalyst_headlines"] = external_info.get("catalyst_headlines") or []
            candidate["catalyst_source_count"] = external_info.get("catalyst_source_count") or 0
            candidate["catalyst_origin"] = "external_catalysts"
        else:
            candidate["catalyst_origin"] = "none"
        candidate.update(score_candidate(candidate))
        candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
        candidate["reasons"] = _dedup_messages(candidate.get("reasons"))

    if use_ohlcv_levels and max(0, int(ohlcv_top_n)) > 0:
        ranked_for_ohlcv = _rank_candidates(candidates)
        ohlcv_level_symbols = [c["ticker"] for c in ranked_for_ohlcv[: max(0, int(ohlcv_top_n))]]
        try:
            ohlcv_levels_map, ohlcv_warnings, ohlcv_level_diag = fetch_intraday_ohlcv_levels(
                ohlcv_level_symbols, interval=ohlcv_interval, count=100
            )
            global_warnings.extend(ohlcv_warnings)
        except Exception as exc:
            global_warnings.append(f"get_ohlcv intradía falló globalmente: {exc}")
        ohlcv_symbol_keys = {x.upper() for x in ohlcv_level_symbols}
        for candidate in candidates:
            key = candidate["ticker"].upper()
            if key not in ohlcv_symbol_keys:
                continue
            levels = ohlcv_levels_map.get(key) or ohlcv_levels_map.get(f"NASDAQ:{key}") or {}
            if not levels:
                candidate["warnings"].append("niveles intradía OHLCV no disponibles")
                candidate.update(score_candidate(candidate))
                candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
                candidate["reasons"] = _dedup_messages(candidate.get("reasons"))
                continue
            candidate.update(levels)
            levels_observed = _observation_timestamp(levels)
            for field in ("intraday_high", "intraday_low", "last_close_intraday", "approx_intraday_vwap_from_bars"):
                candidate["data_provenance"][field] = build_field_provenance(
                    field=field,
                    value=candidate.get(field),
                    source=f"tvremix:get_ohlcv:{ohlcv_interval}",
                    observed_at=levels_observed,
                    received_at=run_started_at,
                )
            candidate.update(score_candidate(candidate))
            candidate["warnings"] = _dedup_messages(candidate.get("warnings"))
            candidate["reasons"] = _dedup_messages(candidate.get("reasons"))

    no_headlines_symbols = 0
    no_earnings_parseable_symbols = 0
    for candidate in candidates:
        if candidate["ticker"].upper() not in catalyst_symbol_keys:
            continue
        if not skip_news and not candidate.get("latest_news_titles"):
            no_headlines_symbols += 1
        if not skip_earnings and not candidate.get("earnings_items"):
            no_earnings_parseable_symbols += 1

    if use_external_catalysts and external_catalysts_not_configured:
        global_warnings.append("external_catalysts: fuente externa de catalizadores no configurada")

    if not skip_news and no_headlines_symbols:
        global_warnings.append(f"get_news sin titulares parseables para {no_headlines_symbols} símbolos")

    if not skip_earnings and no_earnings_parseable_symbols:
        global_warnings.append(f"get_earnings_calendar sin datos parseables para {no_earnings_parseable_symbols} símbolos")

    if earnings_rate_limit_reached:
        global_warnings.append("rate limit alcanzado en earnings; se detuvieron consultas adicionales")

    deduped_global_warnings = []
    seen = set()
    for warning in global_warnings:
        key = warning.strip()
        if not key:
            continue
        if "get_news" in key and "sin titulares parseables" not in key and "fallo global" not in key and "rate limit" not in key:
            continue
        if "get_earnings_calendar" in key and "sin datos parseables" not in key and "fallo global" not in key and "rate limit" not in key:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped_global_warnings.append(key)

    ranked_final = _rank_candidates(candidates)

    technical_batch_available = sum(
        1 for c in candidates if c.get("ticker", "").upper() in technical_symbol_keys and (c.get("technical_rating") not in (None, "") or c.get("rsi") not in (None, ""))
    )
    technical_unavailable = max(len(technical_symbols) - technical_batch_available, 0)

    quotes_available = sum(1 for c in candidates if c.get("price") not in (None, ""))
    intraday_available = sum(1 for c in candidates if c.get("intraday_close") not in (None, ""))
    rvol_available = sum(1 for c in candidates if c.get("rvol_10d") not in (None, ""))
    vwap_available = sum(1 for c in candidates if c.get("vwap") not in (None, ""))
    premarket_available = sum(
        1 for c in candidates if c.get("premarket_change") not in (None, "") or c.get("premarket_gap") not in (None, "")
    )
    technicals_available = sum(1 for c in candidates if c.get("technical_rating") not in (None, "") or c.get("rsi") not in (None, ""))
    relative_strength_available = sum(1 for c in candidates if c.get("relative_strength_vs_qqq") not in (None, ""))

    candidates_with_core_market_data = sum(
        1
        for c in candidates
        if c.get("price") not in (None, "")
        and c.get("volume") not in (None, "")
        and c.get("change_percent") not in (None, "")
    )

    catalyst_queries_enabled = top_n > 0 and ((not skip_news) or (not skip_earnings))
    technicals_required = technical_n > 0

    critical_warning_markers = (
        "rate limit alcanzado en técnicos",
        "analyze_multi_timeframe_batch falló globalmente",
        "rate limit alcanzado: se omiten noticias/earnings restantes",
        "get_quotes",
    )
    has_critical_data_warning = any(
        any(marker in warning for marker in critical_warning_markers)
        for warning in deduped_global_warnings
    )

    degraded_reasons = [
        quotes_available == 0,
        candidates_with_core_market_data == 0,
        technicals_required and technicals_available == 0,
        has_critical_data_warning and (quotes_available == 0 or (technicals_required and technicals_available == 0)),
    ]

    if any(degraded_reasons):
        scanner_mode = "degraded"
    elif use_intraday and intraday_available > 0 and catalyst_queries_enabled:
        scanner_mode = "intraday_plus_catalysts"
    elif use_intraday and intraday_available > 0:
        scanner_mode = "technical_intraday"
    elif catalyst_queries_enabled:
        scanner_mode = "technical_plus_catalysts"
    else:
        scanner_mode = "technical_only"

    ohlcv_visible_in_top = sum(
        1
        for c in ranked_final[:shown_limit]
        if c.get("intraday_high") not in (None, "")
    )
    ohlcv_intraday_requested = int(ohlcv_level_diag.get("ohlcv_intraday_requested", 0))
    if ohlcv_intraday_requested > 0 and ohlcv_visible_in_top < ohlcv_intraday_requested:
        deduped_global_warnings.append(
            f"OHLCV calculado para {ohlcv_intraday_requested} candidatos; {ohlcv_visible_in_top} visible en Top mostrado tras reordenación."
        )

    result = {
        "run_id": run_id,
        "run_started_at": run_started_at.isoformat(),
        "symbols_in_universe": len(symbols),
        "candidates_evaluated": len(candidates),
        "candidates_shown": min(shown_limit, len(ranked_final)),
        "quotes_available": quotes_available,
        "intraday_available": intraday_available,
        "rvol_available": rvol_available,
        "vwap_available": vwap_available,
        "premarket_available": premarket_available,
        "qqq_change_percent": qqq_change_percent,
        "relative_strength_available": relative_strength_available,
        "ohlcv_intraday_requested": int(ohlcv_level_diag.get("ohlcv_intraday_requested", 0)),
        "ohlcv_intraday_available": int(ohlcv_level_diag.get("ohlcv_intraday_available", 0)),
        "ohlcv_vwap_available": int(ohlcv_level_diag.get("ohlcv_vwap_available", 0)),
        "ohlcv_visible_in_top": int(ohlcv_visible_in_top),
        "ohlcv_interval": ohlcv_interval,
        "intraday_via_run_screener": intraday_source_counts["run_screener"],
        "intraday_via_get_symbol_data": intraday_source_counts["get_symbol_data"],
        "screener_rows_returned": int(intraday_diagnostics.get("screener_rows_returned", 0)),
        "screener_symbols_matched": int(intraday_diagnostics.get("screener_symbols_matched", 0)),
        "screener_symbol_fields_detected": intraday_diagnostics.get(
            "screener_symbol_fields_detected", []
        ),
        "technicals_available": technicals_available,
        "technicals_batch_available": technical_batch_available,
        "technicals_fallback_individual": technical_fallback_count,
        "technicals_not_available": technical_unavailable,
        "catalysts_queried": len(catalyst_symbols),
        "catalyst_scope": normalized_catalyst_scope,
        "scanner_mode": scanner_mode,
        "candidates": ranked_final[:shown_limit],
        "external_catalysts_enabled": bool(use_external_catalysts),
        "external_catalysts_configured": bool(use_external_catalysts and not external_catalysts_not_configured),
        "global_warnings": deduped_global_warnings,
    }
    result["audit"] = build_scanner_audit(
        run_id=run_id,
        started_at=run_started_at,
        completed_at=datetime.now(timezone.utc),
        universe_symbols=symbols,
        universe_source="config/nasdaq100_symbols.yaml",
        candidates=candidates,
        global_warnings=deduped_global_warnings,
    )
    return result
