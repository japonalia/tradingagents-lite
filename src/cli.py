from __future__ import annotations

import argparse
from pathlib import Path

from src.data_sources.provider import get_market_data
from src.indicators.levels import calculate_levels
from src.indicators.technicals import calculate_technicals
from src.reports.scanner_report import generate_scanner_report
from src.reports.ticker_report import build_markdown_report, write_ticker_report
from src.scanner.nasdaq100_scanner import scan_nasdaq100


def run_ticker_command(ticker: str, source: str = "yfinance") -> Path:
    ticker_data = get_market_data(ticker, source=source)

    technicals = calculate_technicals(ticker_data.history)
    levels = calculate_levels(ticker_data.history)

    report = build_markdown_report(
        ticker=ticker_data.symbol,
        market_data=ticker_data.market_data,
        technicals=technicals,
        levels=levels,
        missing_data=ticker_data.missing_fields,
        history_rows=len(ticker_data.history),
        source=ticker_data.source,
        warnings=ticker_data.warnings,
    )

    for warning in ticker_data.warnings:
        print(f"Aviso [{ticker_data.source}]: {warning}")

    return write_ticker_report(Path("reports/generated"), ticker_data.symbol, report)




def run_scan_nasdaq100_command(source: str = "tvremix", limit: int = 10) -> Path:
    candidates = scan_nasdaq100(source=source, limit=limit)
    return generate_scanner_report(
        candidates=candidates,
        output_path=Path("reports/generated/nasdaq100_scan_report.md"),
        source=source,
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TradingAgents Lite CLI")
    subparsers = parser.add_subparsers(dest="command")

    ticker_parser = subparsers.add_parser("ticker", help="Genera informe para un ticker")
    ticker_parser.add_argument("symbol", help="Ticker, por ejemplo NVDA")
    ticker_parser.add_argument(
        "--source",
        default="yfinance",
        help="Fuente de datos (opciones: yfinance, tvremix)",
    )

    scan_parser = subparsers.add_parser("scan-nasdaq100", help="Escanea universo Nasdaq 100")
    scan_parser.add_argument("--source", default="tvremix", help="Fuente de datos (actual: tvremix)")
    scan_parser.add_argument("--limit", default=10, type=int, help="Cantidad máxima de símbolos")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ticker":
        try:
            output_file = run_ticker_command(args.symbol, source=args.source)
        except Exception as exc:
            print(f"Error al generar informe: {exc}")
            return
        print(f"Informe generado: {output_file}")
        return

    if args.command == "scan-nasdaq100":
        try:
            output_file = run_scan_nasdaq100_command(source=args.source, limit=args.limit)
        except Exception as exc:
            print(f"Error al ejecutar scanner Nasdaq 100: {exc}")
            return
        print(f"Reporte scanner generado: {output_file}")
        return

    parser.print_help()
    return


if __name__ == "__main__":
    main()
