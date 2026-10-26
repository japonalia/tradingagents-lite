from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal


NEW_YORK = ZoneInfo("America/New_York")


def interval_seconds(interval: str) -> int:
    text = str(interval).strip().lower()
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(text) < 2 or text[-1] not in units:
        raise ValueError(f"Intervalo OHLCV no soportado: {interval}")
    return int(text[:-1]) * units[text[-1]]


def normalize_bars(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    aliases = {
        "timestamp": "bar_start", "time": "bar_start", "datetime": "bar_start",
        "date": "bar_start", "Date": "bar_start", "t": "bar_start",
        "open": "open", "Open": "open", "o": "open",
        "high": "high", "High": "high", "h": "high",
        "low": "low", "Low": "low", "l": "low",
        "close": "close", "Close": "close", "c": "close",
        "volume": "volume", "Volume": "volume", "v": "volume",
    }
    frame = frame.rename(columns={key: value for key, value in aliases.items() if key in frame.columns})
    required = ["bar_start", "open", "high", "low", "close", "volume"]
    if any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=required)
    frame = frame[required].copy()
    frame["bar_start"] = pd.to_datetime(frame["bar_start"], errors="coerce", utc=True)
    for column in required[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame.dropna(subset=required)
        .drop_duplicates(subset=["bar_start"], keep="last")
        .sort_values("bar_start")
        .reset_index(drop=True)
    )


def _regular_session(frame: pd.DataFrame, session_date) -> pd.DataFrame:
    # pandas_market_calendars exposes the XNAS venue under the NASDAQ alias.
    schedule = mcal.get_calendar("NASDAQ").schedule(start_date=session_date, end_date=session_date)
    if schedule.empty:
        return frame.iloc[0:0].copy()
    market_open = schedule.iloc[0]["market_open"]
    market_close = schedule.iloc[0]["market_close"]
    mask = (frame["bar_start"] >= market_open) & (frame["bar_start"] < market_close)
    return frame.loc[mask].copy()


def _orb(session: pd.DataFrame, minutes: int) -> dict[str, float | None]:
    if session.empty:
        return {"high": None, "low": None}
    opening = session.iloc[0]["bar_start"]
    window = session[session["bar_start"] < opening + pd.Timedelta(minutes=minutes)]
    if window.empty or window.iloc[-1]["bar_start"] + (session.attrs["interval_delta"]) < opening + pd.Timedelta(minutes=minutes):
        return {"high": None, "low": None}
    return {"high": float(window["high"].max()), "low": float(window["low"].min())}


def derive_intraday_metrics(
    rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    as_of: datetime,
    interval: str = "5m",
    session_date=None,
) -> dict[str, Any]:
    current = as_of.astimezone(timezone.utc)
    seconds = interval_seconds(interval)
    delta = pd.Timedelta(seconds=seconds)
    bars = normalize_bars(rows)
    if bars.empty:
        return {"quality": "unavailable", "reason": "no_parseable_timestamped_bars"}
    bars["bar_end"] = bars["bar_start"] + delta
    completed = bars[bars["bar_end"] <= current].copy()
    resolved_date = session_date or current.astimezone(NEW_YORK).date()
    session = _regular_session(completed, resolved_date)
    session.attrs["interval_delta"] = delta
    if session.empty:
        return {"quality": "unavailable", "reason": "no_completed_regular_session_bars", "session_date": str(resolved_date)}

    first = session.iloc[0]
    last = session.iloc[-1]
    session_open = float(first["open"])
    close = float(last["close"])
    change = close - session_open
    total_volume = float(session["volume"].sum())
    typical = (session["high"] + session["low"] + session["close"]) / 3
    proxy = float((typical * session["volume"]).sum() / total_volume) if total_volume > 0 else None
    lag = max(0.0, (current - last["bar_end"].to_pydatetime()).total_seconds())
    quality = "delayed" if lag <= max(1200, seconds * 2) else "stale"
    result: dict[str, Any] = {
        "session_date": str(resolved_date),
        "observed_at": last["bar_end"].isoformat(),
        "bar_start": last["bar_start"].isoformat(),
        "bar_end": last["bar_end"].isoformat(),
        "source": "tvremix_get_ohlcv",
        "derivation": "timestamped_ohlcv",
        "quality": quality,
        "lag_seconds": lag,
        "bars_used": int(len(session)),
        "last_completed_bar_close": close,
        "session_open": session_open,
        "session_change": change,
        "session_change_percent": (change / session_open) * 100 if session_open else None,
        "session_high": float(session["high"].max()),
        "session_low": float(session["low"].min()),
        "session_volume": total_volume,
        "momentum_completed_bars_percent": (close / float(first["close"]) - 1) * 100 if float(first["close"]) else None,
        "vwap": None,
        "vwap_quality": "unavailable",
        "vwap_reason": "trade_level_or_provider_vwap_unavailable",
        "ohlcv_vwap_proxy_estimated": proxy,
        "ohlcv_vwap_proxy_quality": "estimated" if proxy is not None else "unavailable",
        "ohlcv_vwap_proxy_ranking_credit": 0,
        "rvol": None,
        "rvol_quality": "unavailable",
        "rvol_reason": "insufficient_same_time_historical_intraday_data",
        "discarded_incomplete_bars": int(len(bars) - len(completed)),
    }
    for minutes in (5, 15, 30):
        orb = _orb(session, minutes)
        result[f"orb_{minutes}_high"] = orb["high"]
        result[f"orb_{minutes}_low"] = orb["low"]
    return result


def relative_strength_from_aligned_bars(
    stock_rows: list[dict[str, Any]] | pd.DataFrame,
    qqq_rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    as_of: datetime,
    interval: str = "5m",
) -> dict[str, Any]:
    seconds = interval_seconds(interval)
    cutoff = pd.Timestamp(as_of.astimezone(timezone.utc))
    stock = normalize_bars(stock_rows)
    qqq = normalize_bars(qqq_rows)
    for frame in (stock, qqq):
        frame["bar_end"] = frame["bar_start"] + pd.Timedelta(seconds=seconds)
    stock = stock[stock["bar_end"] <= cutoff]
    qqq = qqq[qqq["bar_end"] <= cutoff]
    common = stock.merge(qqq, on="bar_start", suffixes=("_stock", "_qqq"))
    if common.empty or len(common) < 2:
        return {"relative_strength_vs_qqq": None, "quality": "unavailable", "reason": "qqq_alignment_unverified"}
    stock_return = (common.iloc[-1]["close_stock"] / common.iloc[0]["open_stock"] - 1) * 100
    qqq_return = (common.iloc[-1]["close_qqq"] / common.iloc[0]["open_qqq"] - 1) * 100
    return {
        "relative_strength_vs_qqq": stock_return - qqq_return,
        "stock_return_percent": stock_return,
        "qqq_return_percent": qqq_return,
        "first_common_bar": common.iloc[0]["bar_start"].isoformat(),
        "last_common_bar": common.iloc[-1]["bar_start"].isoformat(),
        "aligned_bars": int(len(common)),
        "quality": "timestamp_verified",
        "reason": None,
    }
