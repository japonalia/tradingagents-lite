from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _fmt(value):
    return "N/A" if value in (None, "") else str(value)


def generate_scanner_report(candidates, output_path, source="tvremix"):
    candidates = [c for c in (candidates or []) if isinstance(c, dict)]
    output = Path(output_path)

    total = len(candidates)
    complete = sum(1 for c in candidates if not c.get("missing_fields"))
    missing = total - complete
    unavailable = sorted({field for c in candidates for field in (c.get("missing_fields") or [])})

    lines = [
        "# Scanner Nasdaq 100",
        "",
        f"- Fecha/hora generación (local): **{datetime.now().astimezone().isoformat(timespec='seconds')}**",
        f"- Fuente primaria: **{source}**",
        "",
        "## Calidad de datos",
        f"- Candidatas evaluadas: **{total}**",
        f"- Completas: **{complete}**",
        f"- Con datos faltantes: **{missing}**",
        f"- Datos no disponibles detectados: **{', '.join(unavailable) if unavailable else 'ninguno'}**",
        "",
        "## Top candidatas",
        "",
        "| Ranking | Ticker | Precio | Variación % | Volumen | Rating técnico | RSI | Score | Riesgo / warnings |",
        "|---:|---|---:|---:|---:|---|---:|---:|---|",
    ]

    for idx, c in enumerate(sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True), start=1):
        warnings = "; ".join(c.get("warnings") or c.get("reasons") or []) or "-"
        lines.append(
            f"| {idx} | {_fmt(c.get('ticker'))} | {_fmt(c.get('price'))} | {_fmt(c.get('change_percent'))} | {_fmt(c.get('volume'))} | {_fmt(c.get('technical_rating'))} | {_fmt(c.get('rsi'))} | {_fmt(c.get('total_score'))} | {warnings} |"
        )

    lines.extend(
        [
            "",
            "## No es señal ejecutable",
            "Este reporte es informativo y no constituye una orden, recomendación ni señal ejecutable de trading.",
            "",
            "Notas de versión: VWAP, RVOL y premarket high/low no están disponibles en esta versión inicial.",
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
