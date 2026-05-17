from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.indicators.levels import calculate_levels
from src.indicators.technicals import calculate_technicals
from src.reports.ticker_report import build_markdown_report


def _load_sample_history(csv_path: Path) -> pd.DataFrame:
    history = pd.read_csv(csv_path)
    required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required_columns if column not in history.columns]
    if missing:
        raise ValueError(f"El CSV no contiene columnas requeridas: {', '.join(missing)}")

    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    history = history.dropna(subset=["Date"]).sort_values("Date")

    numeric_columns = ["Open", "High", "Low", "Close", "Volume"]
    for column in numeric_columns:
        history[column] = pd.to_numeric(history[column], errors="coerce")

    history = history.dropna(subset=["Open", "High", "Low", "Close"])
    return history


def generate_sample_report() -> Path:
    sample_csv = Path("data/sample/NVDA_sample_daily.csv")
    output_path = Path("reports/generated/NVDA_sample_report.md")

    history = _load_sample_history(sample_csv)
    technicals = calculate_technicals(history)
    levels = calculate_levels(history)

    last = history.iloc[-1]
    previous_close = history["Close"].iloc[-2] if len(history) > 1 else last["Close"]
    change = float(last["Close"] - previous_close)
    change_percent = (change / float(previous_close) * 100) if previous_close else None

    market_data = {
        "last_price": float(last["Close"]),
        "change": change,
        "change_percent": change_percent,
        "volume": int(last["Volume"]) if pd.notna(last["Volume"]) else None,
        "market_cap": None,
        "pe_ratio": None,
        "eps": None,
        "week52_low": float(history["Low"].min()),
        "week52_high": float(history["High"].max()),
    }

    report = build_markdown_report(
        ticker="NVDA_SAMPLE",
        market_data=market_data,
        technicals=technicals,
        levels=levels,
        missing_data=["market_cap", "pe_ratio", "eps"],
        history_rows=len(history),
        source="sample",
        warnings=[],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    report_path = generate_sample_report()
    print(f"Informe de muestra generado: {report_path}")
