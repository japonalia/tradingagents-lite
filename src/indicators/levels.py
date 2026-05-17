from __future__ import annotations

import pandas as pd


def _last_window(values: pd.Series, window: int) -> pd.Series:
    if values.empty:
        return values
    return values.tail(min(window, len(values)))


def calculate_levels(history: pd.DataFrame) -> dict[str, float | None]:
    if history.empty or "Close" not in history.columns:
        return {
            "support_recent": None,
            "resistance_recent": None,
            "high_20": None,
            "low_20": None,
            "high_50": None,
            "low_50": None,
        }

    close = history["Close"].dropna()
    if close.empty:
        return {
            "support_recent": None,
            "resistance_recent": None,
            "high_20": None,
            "low_20": None,
            "high_50": None,
            "low_50": None,
        }

    recent = _last_window(close, 20)
    window_20 = _last_window(close, 20)
    window_50 = _last_window(close, 50)

    return {
        "support_recent": float(recent.min()) if not recent.empty else None,
        "resistance_recent": float(recent.max()) if not recent.empty else None,
        "high_20": float(window_20.max()) if not window_20.empty else None,
        "low_20": float(window_20.min()) if not window_20.empty else None,
        "high_50": float(window_50.max()) if not window_50.empty else None,
        "low_50": float(window_50.min()) if not window_50.empty else None,
    }
