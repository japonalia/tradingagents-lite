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
    technicals_available = int((metrics or {}).get("technicals_available", 0))
    catalysts_queried = int((metrics or {}).get("catalysts_queried", 0))
    technicals_batch_available = int((metrics or {}).get("technicals_batch_available", 0))
    technicals_fallback_individual = int((metrics or {}).get("technicals_fallback_individual", 0))
    technicals_not_available = int((metrics or {}).get("technicals_not_available", 0))
    complete = sum(1 for c in candidates if not c.get("missing_fields"))
    missing = total - complete
    unavailable = sorted({field for c in candidates for field in (c.get("missing_fields") or [])})

    gw = [str(w) for w in (global_warnings or []) if str(w).strip()]

    lines = [
        "# Scanner Nasdaq 100",
        "",
        f"- Fecha/hora generación (local): **{datetime.now().astimezone().isoformat(timespec='seconds')}**",
        f"- Fuente primaria: **{source}**",
        "",
        "## Calidad de datos",
        f"- Símbolos en universo: **{symbols_in_universe}**",
        f"- Candidatas evaluadas: **{total}**",
        f"- Candidatas mostradas: **{shown}**",
        f"- Quotes disponibles: **{quotes_available}**",
        f"- Técnicos disponibles: **{technicals_available}**",
        f"- Técnicos batch disponibles: **{technicals_batch_available}**",
        f"- Técnicos fallback individuales: **{technicals_fallback_individual}**",
        f"- Técnicos no disponibles: **{technicals_not_available}**",
        f"- Catalizadores consultados: **{catalysts_queried}**",
        f"- Completas: **{complete}**",
        f"- Con datos faltantes: **{missing}**",
        f"- Datos no disponibles detectados: **{', '.join(unavailable) if unavailable else 'ninguno'}**",
        "",
        "## Top candidatas",
        "",
        "| Ranking | Ticker | Precio | Variación % | Volumen | Rating técnico | RSI | Catalizador | Score | Riesgo / warnings |",
        "|---:|---|---:|---:|---:|---|---:|---|---:|---|",
    ]

    sorted_candidates = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)

    for idx, c in enumerate(sorted_candidates, start=1):
        local_warnings = [str(w)[:120] for w in (c.get("warnings") or c.get("reasons") or [])]
        warnings = "; ".join(local_warnings[:3]) or "-"
        tech_summary = (c.get("technical_batch_summary") or "").strip()
        if tech_summary:
            compact = " ".join(tech_summary.split())[:120]
            if compact:
                warnings = f"{warnings}; tech_batch: {compact}" if warnings != "-" else f"tech_batch: {compact}"
        lines.append(
            f"| {idx} | {_fmt(c.get('ticker'))} | {_fmt(c.get('price'))} | {_fmt(c.get('change_percent'))} | {_fmt(c.get('volume'))} | {_fmt(c.get('technical_rating'))} | {_fmt(c.get('rsi'))} | {_fmt(c.get('catalyst_summary'))} | {_fmt(c.get('total_score'))} | {warnings} |"
        )

    lines.extend(["", "## Warnings globales", ""])
    if gw:
        for warning in gw:
            lines.append(f"- {warning}")
    else:
        lines.append("- Ninguno")

    lines.extend(["", "## Catalizadores detectados", ""])
    for c in sorted_candidates[: min(5, len(sorted_candidates))]:
        ticker = _fmt(c.get("ticker"))
        lines.append(f"### {ticker}")
        lines.append(f"- Resumen: {_fmt(c.get('catalyst_summary'))}")
        titles = c.get("latest_news_titles") or []
        if titles:
            lines.append("- Titulares:")
            for title in titles:
                lines.append(f"  - {title}")
        else:
            lines.append("- Titulares: ninguno")

        earnings_items = c.get("earnings_items") or []
        if earnings_items:
            lines.append(f"- Earnings: {len(earnings_items)} evento(s) detectado(s)")
        else:
            lines.append("- Earnings: no detectados")

        catalyst_warnings = c.get("catalyst_warnings") or []
        lines.append(f"- Warnings: {'; '.join(catalyst_warnings) if catalyst_warnings else 'ninguno'}")
        lines.append("")

    top_with_batch = [c for c in sorted_candidates if any(c.get(k) not in (None, "") for k in ("adx", "atr", "confluence_alignment", "week_52_high", "week_52_low"))][:5]
    if top_with_batch:
        lines.extend(["## Técnicos batch destacados (Top 5)", ""])
        for c in top_with_batch:
            lines.append(
                f"- **{_fmt(c.get('ticker'))}**: ADX={_fmt(c.get('adx'))}, ATR={_fmt(c.get('atr'))}, confluence={_fmt(c.get('confluence_alignment'))}, 52w=[{_fmt(c.get('week_52_low'))} - {_fmt(c.get('week_52_high'))}]"
            )
        lines.append("")

    lines.extend(
        [
            "## No es señal ejecutable",
            "Este reporte es informativo y no constituye una orden, recomendación ni señal ejecutable de trading.",
            "",
            "VWAP, RVOL y premarket high/low siguen no disponibles en esta versión.",
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
