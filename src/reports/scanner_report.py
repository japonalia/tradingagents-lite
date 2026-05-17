from __future__ import annotations

from pathlib import Path


def generate_scanner_report(candidates, output_path):
    """Genera un reporte Markdown básico para el scanner Nasdaq 100 (placeholder)."""
    candidates = list(candidates or [])
    output = Path(output_path)

    lines = [
        "# Scanner Nasdaq 100",
        "",
        "## Calidad de datos",
    ]

    if candidates:
        complete = 0
        for candidate in candidates:
            missing = candidate.get("missing_fields") if isinstance(candidate, dict) else None
            if not missing:
                complete += 1
        lines.append(f"- Candidatas recibidas: **{len(candidates)}**")
        lines.append(f"- Candidatas con datos completos: **{complete}**")
        lines.append(f"- Candidatas con datos faltantes: **{len(candidates) - complete}**")
    else:
        lines.append("- No se recibieron candidatas todavía.")

    lines.extend(["", "## Top candidatas"])

    if candidates:
        ranked = sorted(
            [candidate for candidate in candidates if isinstance(candidate, dict)],
            key=lambda item: item.get("total_score", 0),
            reverse=True,
        )
        for index, candidate in enumerate(ranked[:5], start=1):
            ticker = candidate.get("ticker", "N/A")
            score = candidate.get("total_score", 0)
            lines.append(f"{index}. **{ticker}** — score: `{score}`")
    else:
        lines.append("_Sin candidatas para mostrar por ahora._")

    lines.extend(
        [
            "",
            "> Nota: el scanner real de Nasdaq 100 se implementará en una fase posterior.",
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
