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
) -> str:
    missing_text = ", ".join(missing_data) if missing_data else "Ninguno"

    lines = [
        f"# Informe bruto para {ticker}",
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
        f"- Máximo 20 sesiones: {_fmt_number(levels.get('high_20'))}",
        f"- Mínimo 20 sesiones: {_fmt_number(levels.get('low_20'))}",
        f"- Máximo 50 sesiones: {_fmt_number(levels.get('high_50'))}",
        f"- Mínimo 50 sesiones: {_fmt_number(levels.get('low_50'))}",
        "",
        "## Datos no disponibles",
        f"- {missing_text}",
        "",
        "## Bloque para pegar en GPT TradingAgents",
        "```text",
        f"Ticker: {ticker}",
        f"Precio último: {_fmt_number(market_data.get('last_price'))}",
        f"Cambio diario: {_fmt_number(market_data.get('change'))} ({_fmt_number(market_data.get('change_percent'))}%)",
        f"SMA20/SMA50/SMA200: {_fmt_number(technicals.get('sma_20'))} / {_fmt_number(technicals.get('sma_50'))} / {_fmt_number(technicals.get('sma_200'))}",
        f"RSI14: {_fmt_number(technicals.get('rsi_14'))}",
        f"MACD/Signal/Hist: {_fmt_number(technicals.get('macd'))} / {_fmt_number(technicals.get('macd_signal'))} / {_fmt_number(technicals.get('macd_histogram'))}",
        f"ATR14: {_fmt_number(technicals.get('atr_14'))}",
        f"Soporte/Resistencia reciente: {_fmt_number(levels.get('support_recent'))} / {_fmt_number(levels.get('resistance_recent'))}",
        f"Max/Min 20: {_fmt_number(levels.get('high_20'))} / {_fmt_number(levels.get('low_20'))}",
        f"Max/Min 50: {_fmt_number(levels.get('high_50'))} / {_fmt_number(levels.get('low_50'))}",
        f"Campos no disponibles: {missing_text}",
        "No usar este bloque para ejecutar trading automático.",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_ticker_report(output_dir: Path, ticker: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{ticker}_report.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path
