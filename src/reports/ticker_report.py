from __future__ import annotations

from pathlib import Path
from typing import Any


def _fmt_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "No disponible"
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return "No disponible"


def _fmt_int(value: Any) -> str:
    if value is None:
        return "No disponible"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "No disponible"


def build_markdown_report(
    ticker: str,
    market_data: dict[str, Any],
    technicals: dict[str, Any],
    levels: dict[str, Any],
    missing_data: list[str],
    history_rows: int,
    source: str = "yfinance",
    warnings: list[str] | None = None,
) -> str:
    warnings = warnings or []
    missing_text = ", ".join(missing_data) if missing_data else "Ninguno"

    tv_quote = market_data.get("quote", {}) if source == "tvremix" else {}
    tv_technicals = market_data.get("technicals", {}) if source == "tvremix" else {}
    tv_financials = market_data.get("financials", {}) if source == "tvremix" else {}
    tv_news = market_data.get("news", []) if source == "tvremix" else []

    lines = [
        f"# Informe bruto para {ticker}",
        "",
        f"- Fuente primaria: {source}",
        "",
        "## Datos de mercado",
        f"- Precio último: {_fmt_number(market_data.get('last_price'))}",
        f"- Variación: {_fmt_number(market_data.get('change'))}",
        f"- Variación %: {_fmt_number(market_data.get('change_percent'))}",
        f"- Volumen: {_fmt_int(market_data.get('volume'))}",
        f"- Market cap: {_fmt_int(market_data.get('market_cap'))}",
        f"- PER: {_fmt_number(market_data.get('pe_ratio'))}",
        f"- EPS: {_fmt_number(market_data.get('eps'))}",
        f"- Rango 52 semanas: {_fmt_number(market_data.get('week52_low'))} - {_fmt_number(market_data.get('week52_high'))}",
        "",
    ]

    if source == "tvremix":
        lines.extend(
            [
                "## TVRemix: payloads mapeados",
                f"- Símbolo TVRemix: {market_data.get('tv_symbol', 'No disponible')}",
                f"- Quote keys: {', '.join(sorted(tv_quote.keys())) if isinstance(tv_quote, dict) and tv_quote else 'No disponible'}",
                f"- Technicals keys: {', '.join(sorted(tv_technicals.keys())) if isinstance(tv_technicals, dict) and tv_technicals else 'No disponible'}",
                f"- Financials keys: {', '.join(sorted(tv_financials.keys())) if isinstance(tv_financials, dict) and tv_financials else 'No disponible'}",
                "",
                "### Indicadores (TVRemix get_technicals)",
                f"- RSI: {_fmt_number(tv_technicals.get('rsi') or tv_technicals.get('rsi_14'))}",
                f"- MACD: {_fmt_number(tv_technicals.get('macd'))}",
                f"- SMA 20: {_fmt_number(tv_technicals.get('sma_20') or tv_technicals.get('sma20'))}",
                f"- SMA 50: {_fmt_number(tv_technicals.get('sma_50') or tv_technicals.get('sma50'))}",
                "",
                "### Fundamentales (TVRemix get_financials)",
                f"- Revenue: {_fmt_number(tv_financials.get('revenue'), 0)}",
                f"- EBITDA: {_fmt_number(tv_financials.get('ebitda'), 0)}",
                f"- Debt: {_fmt_number(tv_financials.get('debt') or tv_financials.get('total_debt'), 0)}",
                "",
                "### Titulares (TVRemix get_news)",
            ]
        )
        if isinstance(tv_news, list) and tv_news:
            for idx, item in enumerate(tv_news[:5], start=1):
                title = item.get("title") or item.get("headline") or "Sin título"
                source_name = item.get("source") or item.get("publisher") or "Fuente desconocida"
                lines.append(f"- [{idx}] {title} ({source_name})")
        else:
            lines.append("- No disponible")
        lines.append("")

    lines.extend(
        [
            "## Calidad de datos",
            f"- Filas históricas diarias disponibles: {history_rows}",
            f"- Campos no disponibles en la fuente: {missing_text}",
            "",
            "## Indicadores técnicos",
            f"- SMA 20: {_fmt_number(technicals.get('sma_20'))}",
            f"- SMA 50: {_fmt_number(technicals.get('sma_50'))}",
            f"- SMA 200: {_fmt_number(technicals.get('sma_200'))}",
            f"- RSI 14: {_fmt_number(technicals.get('rsi_14'))}",
            f"- MACD: {_fmt_number(technicals.get('macd'))}",
            f"- MACD señal: {_fmt_number(technicals.get('macd_signal'))}",
            f"- MACD histograma: {_fmt_number(technicals.get('macd_histogram'))}",
            f"- ATR 14: {_fmt_number(technicals.get('atr_14'))}",
            "",
            "## Niveles",
            f"- Soporte aproximado reciente: {_fmt_number(levels.get('support_recent'))}",
            f"- Resistencia aproximada reciente: {_fmt_number(levels.get('resistance_recent'))}",
            "",
            "## Warnings",
        ]
    )

    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- Ninguno")

    lines.extend(["", "## Datos no disponibles", f"- {missing_text}", ""])
    return "\n".join(lines)


def write_ticker_report(output_dir: Path, ticker: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{ticker}_report.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path
