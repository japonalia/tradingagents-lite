from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DataQualityState(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    STALE = "stale"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw /= 1000.0
        try:
            parsed = datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_hint(hint: Any) -> DataQualityState | None:
    text = str(hint or "").strip().lower()
    aliases = {
        "realtime": DataQualityState.LIVE,
        "real_time": DataQualityState.LIVE,
        "live": DataQualityState.LIVE,
        "delayed": DataQualityState.DELAYED,
        "stale": DataQualityState.STALE,
        "estimated": DataQualityState.ESTIMATED,
        "estimate": DataQualityState.ESTIMATED,
        "unavailable": DataQualityState.UNAVAILABLE,
        "missing": DataQualityState.UNAVAILABLE,
        "unknown": DataQualityState.UNKNOWN,
    }
    return aliases.get(text)


def build_field_provenance(
    *,
    field: str,
    value: Any,
    source: str,
    observed_at: Any = None,
    received_at: datetime | None = None,
    quality_hint: Any = None,
    live_max_age_seconds: int = 120,
    delayed_max_age_seconds: int = 1_200,
) -> dict[str, Any]:
    """Create an explicit, conservative provenance record.

    A present value without a parseable observation time is ``unknown`` rather
    than ``live``. Explicit ``estimated`` and ``stale`` hints always win.
    """
    received = (received_at or utc_now()).astimezone(timezone.utc)
    observed = parse_timestamp(observed_at)
    hint = _normalize_hint(quality_hint)
    reasons: list[str] = []

    if value in (None, "", "N/A"):
        state = DataQualityState.UNAVAILABLE
        reasons.append("value_missing")
    elif hint in {DataQualityState.ESTIMATED, DataQualityState.STALE, DataQualityState.UNAVAILABLE}:
        state = hint
        reasons.append(f"explicit_quality_hint:{hint.value}")
    elif observed is None:
        state = hint if hint in {DataQualityState.DELAYED, DataQualityState.UNKNOWN} else DataQualityState.UNKNOWN
        reasons.append("observation_timestamp_missing_or_invalid")
    else:
        raw_age_seconds = (received - observed).total_seconds()
        age_seconds = max(0.0, raw_age_seconds)
        if raw_age_seconds < -60:
            state = DataQualityState.UNKNOWN
            reasons.append("observation_timestamp_is_in_the_future")
        elif hint == DataQualityState.DELAYED:
            state = DataQualityState.DELAYED
            reasons.append("explicit_quality_hint:delayed")
        elif age_seconds <= live_max_age_seconds:
            state = DataQualityState.LIVE
            reasons.append("within_live_freshness_window")
        elif age_seconds <= delayed_max_age_seconds:
            state = DataQualityState.DELAYED
            reasons.append("outside_live_within_delayed_window")
        else:
            state = DataQualityState.STALE
            reasons.append("outside_delayed_freshness_window")

    age = None if observed is None else round(max(0.0, (received - observed).total_seconds()), 3)
    return {
        "field": field,
        "source": str(source or "unknown"),
        "observed_at": observed.isoformat() if observed else None,
        "received_at": received.isoformat(),
        "age_seconds": age,
        "quality_state": state.value,
        "is_usable_for_live_claim": state == DataQualityState.LIVE,
        "reasons": reasons,
    }
