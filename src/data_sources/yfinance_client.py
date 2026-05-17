from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf


@dataclass
class TickerData:
    ticker: str
    market_data: dict[str, Any]
    history: pd.DataFrame
    missing_fields: list[str]


def _safe_get(info: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def fetch_ticker_data(ticker: str, period: str = "1y") -> TickerData:
    symbol = ticker.upper().strip()
    if not symbol:
        raise ValueError("El ticker no puede estar vacío.")

    yf_ticker = yf.Ticker(symbol)

    try:
        info = yf_ticker.info or {}
    except Exception:
        info = {}

    history = yf_ticker.history(period=period, interval="1d", auto_adjust=False)
    if history is None:
        history = pd.DataFrame()

    mapping = {
        "last_price": _safe_get(info, "regularMarketPrice", "currentPrice"),
        "change": _safe_get(info, "regularMarketChange"),
        "change_percent": _safe_get(info, "regularMarketChangePercent"),
        "volume": _safe_get(info, "regularMarketVolume", "volume"),
        "market_cap": _safe_get(info, "marketCap"),
        "pe_ratio": _safe_get(info, "trailingPE", "forwardPE"),
        "eps": _safe_get(info, "trailingEps", "forwardEps"),
        "week52_low": _safe_get(info, "fiftyTwoWeekLow"),
        "week52_high": _safe_get(info, "fiftyTwoWeekHigh"),
    }

    missing_fields = [key for key, value in mapping.items() if value is None]

    return TickerData(
        ticker=symbol,
        market_data=mapping,
        history=history,
        missing_fields=missing_fields,
    )
