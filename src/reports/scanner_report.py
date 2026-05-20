from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _fmt(value):
    return "N/A" if value in (None, "") else str(value)


def _dedup_texts(values):
    seen = set()
    deduped = []
    for value in values or []:
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            deduped.append(text)
    return deduped


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_severe_warning(warnings):
    severe_keywords = (
        "grave",
        "severo",
        "halt",
        "suspend",
        "no disponible",
        "missing",
        "fall",
        "error",
    )
    for warning in warnings:
        text = str(warning).strip().lower()
        if any(keyword in text for keyword in severe_keywords):
            return True
    return False


def _has_confirmed_catalyst(candidate):
    if candidate.get("has_recent_catalyst"):
        return True
    summary = str(candidate.get("catalyst_summary") or "").strip().lower()
    if not summary:
        return False
    for marker in ("sin catalizador", "sin titulares", "no se detectaron"):
        if marker in summary:
            return False
    return True


def _compute_day_trade_status(candidate, warnings):
    rvol = _to_float(candidate.get("rvol_10d"))
    rs = _to_float(candidate.get("relative_strength_vs_qqq"))
    price = _to_float(candidate.get("price"))
    vwap = _to_float(candidate.get("vwap"))
    severe = _has_severe_warning(warnings)
    confirmed_catalyst = _has_confirmed_catalyst(candidate)

    if severe or (rvol is not None and rvol < 0.5):
        return "no_trade_quality", "Warning grave o RVOL crítico (<0.5) en la candidata principal."
    if (
        rvol is not None and rvol >= 1.5
        and rs is not None and rs >= 1
        and price is not None and vwap is not None and price >= vwap
        and not severe
        and (confirmed_catalyst or rvol >= 2)
    ):
        return "clear_candidate", "Momentum, flujo y estructura intradía alineados con confirmación suficiente."
    if (
        rs is not None and rs >= 1
        and price is not None and vwap is not None and price >= vwap
        and rvol is not None and rvol >= 0.75
        and not confirmed_catalyst
    ):
        return "technical_candidate_only", "Setup técnico válido, pero sin catalizador real confirmado."
    if rs is not None and rs > 0 and rvol is not None and rvol < 0.75:
        return "weak_candidate", "Hay fuerza relativa, pero el volumen no confirma el movimiento."
    return "technical_candidate_only", "Lectura técnica aceptable, pero sin señal de alta convicción."


def generate_scanner_report(candidates, output_path, source="tvremix", global_warnings=None, metrics=None):
    candidates = [c for c in (candidates or []) if isinstance(c, dict)]
    output = Path(output_path)

    total = int((metrics or {}).get("candidates_evaluated", len(candidates)))
    symbols_in_universe = int((metrics or {}).get("symbols_in_universe", total))
    shown = int((metrics or {}).get("candidates_shown", len(candidates)))
    quotes_available = int((metrics or {}).get("quotes_available", 0))
    intraday_available = int((metrics or {}).get("intraday_available", 0))
    rvol_available = int((metrics or {}).get("rvol_available", 0))
    vwap_available = int((metrics or {}).get("vwap_available", 0))
    premarket_available = int((metrics or {}).get("premarket_available", 0))
    intraday_via_run_screener = int((metrics or {}).get("intraday_via_run_screener", 0))
    intraday_via_get_symbol_data = int((metrics or {}).get("intraday_via_get_symbol_data", 0))
    technicals_available = int((metrics or {}).get("technicals_available", 0))
    catalysts_queried = int((metrics or {}).get("catalysts_queried", 0))
    technicals_batch_available = int((metrics or {}).get("technicals_batch_available", 0))
    technicals_fallback_individual = int((metrics or {}).get("technicals_fallback_individual", 0))
    technicals_not_available = int((metrics or {}).get("technicals_not_available", 0))
    scanner_mode = str((metrics or {}).get("scanner_mode", "degraded")).strip() or "degraded"
    qqq_change_percent = (metrics or {}).get("qqq_change_percent")
    relative_strength_available = int((metrics or {}).get("relative_strength_available", 0))
    ohlcv_intraday_requested = int((metrics or {}).get("ohlcv_intraday_requested", 0))
    ohlcv_intraday_available = int((metrics or {}).get("ohlcv_intraday_available", 0))
    ohlcv_vwap_available = int((metrics or {}).get("ohlcv_vwap_available", 0))
    ohlcv_visible_in_top = int((metrics or {}).get("ohlcv_visible_in_top", 0))
    complete = sum(1 for c in candidates if not c.get("missing_fields"))
    missing = total - complete
    unavailable = sorted({field for c in candidates for field in (c.get("missing_fields") or [])})

    gw = [str(w) for w in (global_warnings or []) if str(w).strip()]

    lines = ["# Scanner Nasdaq 100", "", f"- Fecha/hora generación (local): **{datetime.now().astimezone().isoformat(timespec='seconds')}**", f"- Fuente primaria: **{source}**", "", "## Modo del scanner"]

    if scanner_mode == "technical_only":
        lines.extend(["- technical_only: Scanner técnico sin catalizadores.", "- Este ranking prioriza movimiento, volumen, rating técnico y estructura técnica. No valida catalizador real.", ""])
    elif scanner_mode == "technical_plus_catalysts":
        lines.extend(["- technical_plus_catalysts: Scanner técnico con catalizadores básicos.", ""])
    elif scanner_mode == "technical_intraday":
        lines.extend(["- technical_intraday: Scanner técnico con capa intradía (run_screener + fallback get_symbol_data para Top preliminar).", ""])
    elif scanner_mode == "intraday_plus_catalysts":
        lines.extend(["- intraday_plus_catalysts: Scanner intradía + catalizadores.", ""])
    else:
        lines.extend(["- degraded: Scanner degradado por fallos de datos.", ""])

    lines.extend([
        "## Calidad de datos",
        f"- Símbolos en universo: **{symbols_in_universe}**",
        f"- Candidatas evaluadas: **{total}**",
        f"- Candidatas mostradas: **{shown}**",
        f"- Quotes disponibles: **{quotes_available}**",
        f"- Intradía disponibles: **{intraday_available}**",
        f"- RVOL disponibles: **{rvol_available}**",
        f"- VWAP disponibles: **{vwap_available}**",
        f"- Premarket disponibles: **{premarket_available}**",
        f"- Intradía vía run_screener: **{intraday_via_run_screener}**",
        f"- Intradía vía get_symbol_data: **{intraday_via_get_symbol_data}**",
        f"- Técnicos disponibles: **{technicals_available}**",
        f"- Técnicos batch disponibles: **{technicals_batch_available}**",
        f"- Técnicos fallback individuales: **{technicals_fallback_individual}**",
        f"- Técnicos no disponibles: **{technicals_not_available}**",
        f"- Catalizadores consultados: **{catalysts_queried}**",
        f"- QQQ referencia: **{_fmt(qqq_change_percent)}**",
        f"- Fuerza relativa disponible: **{relative_strength_available}/{total}**",
        f"- OHLCV intradía consultados: **{ohlcv_intraday_requested}**",
        f"- OHLCV intradía disponibles: **{ohlcv_intraday_available}**",
        f"- OHLCV visibles en Top mostrado: **{ohlcv_visible_in_top}**",
        f"- VWAP calculado desde barras disponible: **{ohlcv_vwap_available}**",
        f"- Completas: **{complete}**",
        f"- Con datos faltantes: **{missing}** (incluye símbolos fuera del subconjunto técnico consultado)",
        f"- Datos no disponibles detectados: **{', '.join(unavailable) if unavailable else 'ninguno'}**",
    ])

    sorted_candidates = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
    top_candidate = sorted_candidates[0] if sorted_candidates else {}
    top_warnings = _dedup_texts((top_candidate.get("warnings") or []) + (top_candidate.get("reasons") or []))
    day_trade_candidate_status, status_explanation = _compute_day_trade_status(top_candidate, top_warnings)

    top_rvol = _to_float(top_candidate.get("rvol_10d"))
    top_rs = _to_float(top_candidate.get("relative_strength_vs_qqq"))
    top_price = _to_float(top_candidate.get("price"))
    top_vwap = _to_float(top_candidate.get("vwap"))
    top_change = _to_float(top_candidate.get("change_percent"))
    setup_quality = "Media"
    if (
        top_rvol is not None and top_rvol >= 1.5
        and top_rs is not None and top_rs > 1
        and top_price is not None and top_vwap is not None and top_price > top_vwap
        and not _has_severe_warning(top_warnings)
    ):
        setup_quality = "Alta"
    elif (
        top_rs is not None and top_rs > 0
        and top_price is not None and top_vwap is not None and top_price > top_vwap
        and top_rvol is not None and 0.75 <= top_rvol < 1.5
    ):
        setup_quality = "Media"
    elif (
        (top_rvol is not None and top_rvol < 0.75)
        or (not _has_confirmed_catalyst(top_candidate) and top_change is not None and abs(top_change) >= 4)
    ):
        setup_quality = "Baja"

    lines.extend([
        "",
        "## Resumen ejecutivo para GPT TradingAgents",
        f"- Candidata técnica principal: **{_fmt(top_candidate.get('ticker'))}**",
        f"- Score: **{_fmt(top_candidate.get('total_score'))}**",
        f"- Cambio %: **{_fmt(top_candidate.get('change_percent'))}**",
        f"- RS vs QQQ: **{_fmt(top_candidate.get('relative_strength_vs_qqq'))}**",
        f"- RVOL: **{_fmt(top_candidate.get('rvol_10d'))}**",
        f"- VWAP: **{_fmt(top_candidate.get('vwap'))}**",
        f"- Catalizador: **{_fmt(top_candidate.get('catalyst_summary'))}**",
        f"- Setup quality: **{setup_quality}**",
        f"- Estado candidato: **{day_trade_candidate_status}** — {status_explanation}",
        f"- Nota de riesgo principal: **{'; '.join(top_warnings[:2]) if top_warnings else 'Sin warnings críticos en Top 1.'}**",
        "- Confirmación: **No es señal ejecutable; requiere validación visual y catalizador real.**",
    ])

    rs_top10 = [c for c in sorted_candidates[:10] if _to_float(c.get("relative_strength_vs_qqq")) is not None]
    rs_positive_count = sum(1 for c in rs_top10 if (_to_float(c.get("relative_strength_vs_qqq")) or 0) > 0)
    rvol_sufficient_count = sum(1 for c in sorted_candidates[:10] if (_to_float(c.get("rvol_10d")) or 0) >= 1)
    has_real_catalysts = any(_has_confirmed_catalyst(c) for c in sorted_candidates[:10])
    qqq_direction = "positivo" if (qqq_change_percent is not None and _to_float(qqq_change_percent) is not None and _to_float(qqq_change_percent) >= 0) else "negativo"
    day_action = "acción del día clara" if day_trade_candidate_status == "clear_candidate" else "candidata técnica"

    lines.extend([
        "",
        "## Interpretación rápida del scanner",
        f"- QQQ está **{qqq_direction}** ({_fmt(qqq_change_percent)}%).",
        f"- Top 10: **{rs_positive_count}/10** con RS positiva vs QQQ (sesgo de fuerza relativa {'favorable' if rs_positive_count >= 6 else 'mixto/debilitado'}).",
        f"- RVOL suficiente (>=1.0) en **{rvol_sufficient_count}/10** del Top 10 ({'hay participación' if rvol_sufficient_count >= 5 else 'participación limitada'}).",
        f"- Catalizadores reales en Top 10: **{'sí' if has_real_catalysts else 'no'}**.",
        f"- Lectura operativa: el scanner sugiere **{day_action}**.",
    ])
    lines.extend([
        "",
        "## Top candidatas",
        "",
        "| Ranking | Ticker | Precio | Variación % | RS vs QQQ | Volumen | RVOL | VWAP | Gap/PM | Rating técnico | RSI | Catalizador | Score | Riesgo / warnings |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|---:|---|",
    ])
    for idx, c in enumerate(sorted_candidates, start=1):
        local_warnings = []
        for warning in _dedup_texts((c.get("warnings") or []) + (c.get("reasons") or [])):
            text = warning.strip()
            if text and "summary_markdown" not in text.lower() and not text.lower().startswith("tech_batch:"):
                local_warnings.append(text[:120])
        warnings = "; ".join(_dedup_texts(local_warnings)[:3]) or "-"
        gap_pm = f"g:{_fmt(c.get('gap'))}/pm:{_fmt(c.get('premarket_gap'))}"
        lines.append(f"| {idx} | {_fmt(c.get('ticker'))} | {_fmt(c.get('price'))} | {_fmt(c.get('change_percent'))} | {_fmt(c.get('relative_strength_vs_qqq'))} | {_fmt(c.get('volume'))} | {_fmt(c.get('rvol_10d'))} | {_fmt(c.get('vwap'))} | {gap_pm} | {_fmt(c.get('technical_rating'))} | {_fmt(c.get('rsi'))} | {_fmt(c.get('catalyst_summary'))} | {_fmt(c.get('total_score'))} | {warnings} |")

    lines.extend(["", "## Fuerza relativa vs QQQ", ""])
    rs_candidates = [c for c in sorted_candidates if c.get("relative_strength_vs_qqq") not in (None, "")][:10]
    if rs_candidates:
        lines.append("Top 10:")
        for c in rs_candidates:
            lines.append(f"- {_fmt(c.get('ticker'))}: cambio%={_fmt(c.get('change_percent'))}, QQQ%={_fmt(c.get('qqq_change_percent'))}, RS vs QQQ={_fmt(c.get('relative_strength_vs_qqq'))}")
    else:
        lines.append("- Fuerza relativa no disponible en esta corrida.")

    lines.extend(["", "## Catalizadores reales detectados", ""])
    catalyst_rows = [c for c in sorted_candidates if c.get("has_recent_catalyst")]
    tvremix_rows = [c for c in catalyst_rows if c.get("catalyst_origin") == "tvremix_get_news"]
    external_rows = [c for c in catalyst_rows if c.get("catalyst_origin") == "external_catalysts"]

    lines.append("- TVRemix get_news:")
    if tvremix_rows:
        for c in tvremix_rows[:10]:
            headlines = ", ".join(_dedup_texts(c.get("catalyst_headlines") or c.get("latest_news_titles") or [])[:2]) or "sin titulares"
            lines.append(f"  - {_fmt(c.get('ticker'))}: {_fmt(c.get('catalyst_summary'))} (fuentes={_fmt(c.get('catalyst_source_count'))}) | {headlines}")
    else:
        lines.append("  - Sin catalizadores parseables desde TVRemix.")

    lines.append("- external_catalysts:")
    if external_rows:
        for c in external_rows[:10]:
            headlines = ", ".join(_dedup_texts(c.get("catalyst_headlines") or [])[:2]) or "sin titulares"
            lines.append(f"  - {_fmt(c.get('ticker'))}: {_fmt(c.get('catalyst_summary'))} (fuentes={_fmt(c.get('catalyst_source_count'))}) | {headlines}")
    elif any("external_catalysts: fuente externa de catalizadores no configurada" in w for w in gw):
        lines.append("  - Fuente externa de catalizadores no configurada.")
    else:
        lines.append("  - Sin catalizadores externos detectados en esta corrida.")

    lines.extend(["", "## Niveles intradía destacados", ""])
    level_candidates = [c for c in sorted_candidates if c.get("intraday_high") not in (None, "")]
    if level_candidates:
        lines.extend([
            "| Ticker | High | Low | Último cierre | VWAP barras | Dist. VWAP % | Rango % | Cerca high | Cerca low | Soporte | Resistencia |",
            "|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|",
        ])
        for c in level_candidates:
            lines.append(
                f"| {_fmt(c.get('ticker'))} | {_fmt(c.get('intraday_high'))} | {_fmt(c.get('intraday_low'))} | {_fmt(c.get('last_close_intraday'))} | {_fmt(c.get('approx_intraday_vwap_from_bars'))} | {_fmt(c.get('distance_to_vwap_pct'))} | {_fmt(c.get('intraday_range_pct'))} | {_fmt(c.get('near_intraday_high'))} | {_fmt(c.get('near_intraday_low'))} | {_fmt(c.get('support_intraday'))} | {_fmt(c.get('resistance_intraday'))} |"
            )
    else:
        lines.append("- Sin niveles intradía OHLCV disponibles en esta corrida.")

    lines.extend(["", "## Warnings globales", ""])
    if gw:
        lines.extend([f"- {w}" for w in gw])
    else:
        lines.append("- Ninguno")

    lines.extend(["", "## Datos intradía destacados", ""])
    top_intraday = [c for c in sorted_candidates if c.get("rvol_10d") not in (None, "") or c.get("vwap") not in (None, "")][:10]
    if top_intraday:
        lines.append("Top 10:")
        for c in top_intraday:
            lines.append(f"- {_fmt(c.get('ticker'))}: RVOL={_fmt(c.get('rvol_10d'))}, VWAP={_fmt(c.get('vwap'))}, gap={_fmt(c.get('gap'))}, premarket_high/low={_fmt(c.get('premarket_high'))}/{_fmt(c.get('premarket_low'))}")
    else:
        lines.append("- Sin datos intradía destacados.")

    lines.extend(["", "## Datos faltantes / limitaciones", ""])
    if any("get_news" in w.lower() for w in gw) or catalysts_queried == 0:
        lines.append("- TVRemix get_news no devolvió titulares parseables o fue omitido en esta corrida.")
    if any("earnings" in w.lower() for w in gw):
        lines.append("- Earnings omitidos por configuración (`skip_earnings=True`).")
    if intraday_via_run_screener == 0:
        lines.append("- run_screener sin cobertura útil para la capa intradía en esta corrida.")
    if not has_real_catalysts:
        lines.append("- Catalizadores no confirmados: no hay noticias parseables suficientes en el Top mostrado.")
    if lines[-1] == "":
        lines.append("- Sin limitaciones críticas adicionales en esta corrida.")

    lines.extend(["", "## No es señal ejecutable", "Este reporte es informativo y no constituye una orden, recomendación ni señal ejecutable de trading.", "", "No usar como señal ejecutable intradía.", ""])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
