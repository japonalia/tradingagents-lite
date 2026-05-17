from __future__ import annotations

from src.data_sources.base import MarketDataResult
from src.data_sources.yfinance_client import fetch_ticker_data


def get_market_data(symbol: str, source: str = "yfinance") -> MarketDataResult:
    normalized_source = source.strip().lower()
    if normalized_source != "yfinance":
        raise ValueError("Fuente de datos no soportada todavía")

    return fetch_ticker_data(symbol)
