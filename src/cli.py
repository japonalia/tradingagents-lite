from __future__ import annotations

import argparse
from pathlib import Path

from src.data_sources.yfinance_client import fetch_ticker_data
from src.indicators.levels import calculate_levels
from src.indicators.technicals import calculate_technicals
from src.reports.ticker_report import build_markdown_report, write_ticker_report


def run_ticker_command(ticker: str) -> Path:
    ticker_data = fetch_ticker_data(ticker)

    technicals = calculate_technicals(ticker_data.history)
    levels = calculate_levels(ticker_data.history)

    report = build_markdown_report(
        ticker=ticker_data.ticker,
        market_data=ticker_data.market_data,
        technicals=technicals,
        levels=levels,
        missing_data=ticker_data.missing_fields,
        history_rows=len(ticker_data.history),
    )

    return write_ticker_report(Path("reports/generated"), ticker_data.ticker, report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TradingAgents Lite CLI")
    subparsers = parser.add_subparsers(dest="command")

    ticker_parser = subparsers.add_parser("ticker", help="Genera informe para un ticker")
    ticker_parser.add_argument("symbol", help="Ticker, por ejemplo NVDA")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command != "ticker":
        parser.print_help()
        return

    try:
        output_file = run_ticker_command(args.symbol)
    except Exception as exc:
        print(f"Error al generar informe: {exc}")
        return

    print(f"Informe generado: {output_file}")


if __name__ == "__main__":
    main()
