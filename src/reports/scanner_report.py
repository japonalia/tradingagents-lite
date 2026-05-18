from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _fmt(value):
    return "N/A" if value in (None, "") else str(value)


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
        f"- Completas: **{complete}**",
        f"- Con datos faltantes: **{missing}** (incluye símbolos fuera del subconjunto técnico consultado)",
        f"- Datos no disponibles detectados: **{', '.join(unavailable) if unavailable else 'ninguno'}**",
        "",
        "## Top candidatas",
        "",
        "| Ranking | Ticker | Precio | Variación % | Volumen | RVOL | VWAP | Gap/PM | Rating técnico | RSI | Catalizador | Score | Riesgo / warnings |",
        "|---:|---|---:|---:|---:|---:|---:|---|---|---:|---|---:|---|",
    ])

    sorted_candidates = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
    for idx, c in enumerate(sorted_candidates, start=1):
        local_warnings = []
        for warning in (c.get("warnings") or c.get("reasons") or []):
            text = str(warning).strip()
            if text and "summary_markdown" not in text.lower() and not text.lower().startswith("tech_batch:"):
                local_warnings.append(text[:120])
        warnings = "; ".join(local_warnings[:3]) or "-"
        gap_pm = f"g:{_fmt(c.get('gap'))}/pm:{_fmt(c.get('premarket_gap'))}"
        lines.append(f"| {idx} | {_fmt(c.get('ticker'))} | {_fmt(c.get('price'))} | {_fmt(c.get('change_percent'))} | {_fmt(c.get('volume'))} | {_fmt(c.get('rvol_10d'))} | {_fmt(c.get('vwap'))} | {gap_pm} | {_fmt(c.get('technical_rating'))} | {_fmt(c.get('rsi'))} | {_fmt(c.get('catalyst_summary'))} | {_fmt(c.get('total_score'))} | {warnings} |")

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

    lines.extend(["", "## No es señal ejecutable", "Este reporte es informativo y no constituye una orden, recomendación ni señal ejecutable de trading.", "", "No usar como señal ejecutable intradía.", ""])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
