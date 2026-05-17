from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from src.data_sources.base import MarketDataResult


def _safe_get(info: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def fetch_ticker_data(ticker: str, period: str = "1y") -> MarketDataResult:
    symbol = ticker.upper().strip()
    if not symbol:
        raise ValueError("El ticker no puede estar vacío.")

    warnings: list[str] = []
    yf_ticker = yf.Ticker(symbol)

    try:
        info = yf_ticker.info or {}
    except Exception as exc:
        info = {}
        warnings.append(f"No se pudo obtener metadata de yfinance: {exc}")

    try:
        history = yf_ticker.history(period=period, interval="1d", auto_adjust=False)
    except Exception as exc:
        history = pd.DataFrame()
        warnings.append(f"No se pudo obtener histórico de yfinance: {exc}")

    if history is None:
        history = pd.DataFrame()

    if history.empty:
        warnings.append("Histórico vacío desde yfinance para el símbolo solicitado.")

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
    if missing_fields:
        warnings.append(
            "Campos de mercado no disponibles desde yfinance: "
            + ", ".join(missing_fields)
        )

    return MarketDataResult(
        symbol=symbol,
        source="yfinance",
        market_data=mapping,
        history=history,
        missing_fields=missing_fields,
        warnings=warnings,
    )
