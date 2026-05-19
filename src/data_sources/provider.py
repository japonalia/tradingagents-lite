from __future__ import annotations

from typing import Any

from src.data_sources.base import MarketDataResult
from src.data_sources.tvremix_client import fetch_tvremix_data
from src.data_sources.yfinance_client import fetch_ticker_data


def get_market_data(symbol: str, source: str = "yfinance", **kwargs: Any) -> MarketDataResult:
    normalized_source = source.strip().lower()
    if normalized_source == "yfinance":
        return fetch_ticker_data(symbol)

    if normalized_source == "tvremix":
        try:
            return fetch_tvremix_data(symbol, **kwargs)
        except ValueError:
            raise
        except Exception as exc:
            fallback_result = fetch_ticker_data(symbol)
            fallback_result.warnings.insert(
                0,
                f"TVRemix no disponible ({exc}). Se usa fallback yfinance.",
            )
            return fallback_result

    raise ValueError("Fuente de datos no soportada todavía")
