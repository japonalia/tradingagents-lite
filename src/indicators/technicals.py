from __future__ import annotations

from typing import Any

import pandas as pd


def _to_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _compute_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_atr(history: pd.DataFrame, period: int = 14) -> pd.Series | None:
    required = {"High", "Low", "Close"}
    if not required.issubset(history.columns):
        return None

    high_low = history["High"] - history["Low"]
    high_prev_close = (history["High"] - history["Close"].shift(1)).abs()
    low_prev_close = (history["Low"] - history["Close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def _resolve_price_column(history: pd.DataFrame, preferred: str) -> str | None:
    for column in history.columns:
        if column.lower() == preferred.lower():
            return column
    return None


def calculate_technicals(history: pd.DataFrame) -> dict[str, float | None]:
    close_column = _resolve_price_column(history, "Close")
    if history.empty or close_column is None:
        return {
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "rsi_14": None,
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "atr_14": None,
        }

    close = history[close_column].copy()

    sma_20 = close.rolling(window=20, min_periods=20).mean()
    sma_50 = close.rolling(window=50, min_periods=50).mean()
    sma_200 = close.rolling(window=200, min_periods=200).mean()
    rsi_14 = _compute_rsi(close, 14)
    macd, macd_signal, macd_hist = _compute_macd(close)
    normalized = history.rename(columns={
        _resolve_price_column(history, "High") or "High": "High",
        _resolve_price_column(history, "Low") or "Low": "Low",
        close_column: "Close",
    })
    atr_14 = _compute_atr(normalized, 14)

    return {
        "sma_20": _to_float(sma_20.iloc[-1]),
        "sma_50": _to_float(sma_50.iloc[-1]),
        "sma_200": _to_float(sma_200.iloc[-1]),
        "rsi_14": _to_float(rsi_14.iloc[-1]),
        "macd": _to_float(macd.iloc[-1]),
        "macd_signal": _to_float(macd_signal.iloc[-1]),
        "macd_histogram": _to_float(macd_hist.iloc[-1]),
        "atr_14": _to_float(atr_14.iloc[-1]) if atr_14 is not None else None,
    }
