from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from src.data_quality.provenance import parse_timestamp


CATEGORY_RULES: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("clinical_fda", ("fda", "phase 3", "phase iii", "clinical trial", "drug approval"), 30.0),
    ("m_and_a", ("acquisition", "acquire", "merger", "takeover", "buyout"), 30.0),
    ("earnings", ("earnings", "quarterly results", "revenue", "eps", "profit"), 27.0),
    ("material_contract", ("material contract", "awarded contract", "multi-year contract", "government contract"), 27.0),
    ("guidance", ("guidance", "outlook", "forecast", "raises full-year", "cuts full-year"), 26.0),
    ("regulation_legal", ("regulator", "antitrust", "lawsuit", "settlement", "doj", "sec investigation"), 22.0),
    ("material_partnership", ("strategic partnership", "material partnership", "joint venture"), 21.0),
    ("analyst_shock", ("double upgrade", "double downgrade", "price target", "initiated with"), 18.0),
    ("capital_allocation", ("buyback", "repurchase", "dividend", "debt offering", "share offering"), 18.0),
    ("product_launch", ("launches", "unveils", "new product", "product launch"), 14.0),
    ("management", ("appoints ceo", "ceo resigns", "cfo resigns", "new chief executive"), 12.0),
    ("sympathy_sector", ("sympathy", "sector read-through", "peer results"), 10.0),
    ("macro_commodity", ("interest rate", "inflation", "oil price", "commodity", "tariff"), 8.0),
)

AUTHORITATIVE_DOMAINS = {
    "sec.gov",
    "fda.gov",
    "justice.gov",
    "ftc.gov",
    "nasdaq.com",
}
AUTHORITATIVE_SOURCE_MARKERS = (
    "investor relations",
    "company release",
    "press release",
    "sec filing",
    "fda",
    "department of justice",
    "federal trade commission",
)
RECOGNIZED_SOURCE_MARKERS = (
    "reuters",
    "bloomberg",
    "associated press",
    "wall street journal",
    "financial times",
    "cnbc",
)
POSITIVE_MARKERS = ("beats", "beat estimates", "raises", "approved", "wins", "awarded", "record revenue", "upgrade")
NEGATIVE_MARKERS = ("misses", "missed estimates", "cuts", "rejected", "downgrade", "investigation", "offering")


def _first(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if item.get(key) not in (None, ""):
            return item[key]
    return None


def _headline(item: dict[str, Any]) -> str:
    return str(_first(item, ("title", "headline", "name", "text", "summary")) or "").strip()


def _source_identity(item: dict[str, Any]) -> str:
    source = str(_first(item, ("provider", "source", "publisher", "channel")) or "").strip()
    url = str(item.get("url") or "").strip()
    domain = urlparse(url).netloc.lower().removeprefix("www.") if url else ""
    return domain or source.lower() or "unknown"


def _is_authoritative(item: dict[str, Any]) -> bool:
    identity = _source_identity(item)
    source_text = " ".join(str(item.get(k) or "") for k in ("provider", "source", "publisher", "channel")).lower()
    return any(identity == domain or identity.endswith(f".{domain}") for domain in AUTHORITATIVE_DOMAINS) or any(
        marker in source_text for marker in AUTHORITATIVE_SOURCE_MARKERS
    )


def _is_recognized(item: dict[str, Any]) -> bool:
    identity = _source_identity(item)
    return _is_authoritative(item) or any(marker in identity for marker in RECOGNIZED_SOURCE_MARKERS)


def _category(text: str) -> tuple[str, float]:
    normalized = text.lower()
    for name, markers, materiality in CATEGORY_RULES:
        if any(marker in normalized for marker in markers):
            return name, materiality
    return "other", 5.0


def _freshness_score(published_at: Any, now: datetime) -> tuple[float, float | None]:
    published = parse_timestamp(published_at)
    if published is None:
        return 0.0, None
    age_hours = max(0.0, (now - published).total_seconds() / 3600.0)
    if age_hours <= 6:
        return 15.0, age_hours
    if age_hours <= 24:
        return 12.0, age_hours
    if age_hours <= 72:
        return 8.0, age_hours
    if age_hours <= 168:
        return 4.0, age_hours
    return 0.0, age_hours


def _surprise_and_direction(text: str) -> tuple[float, str]:
    normalized = text.lower()
    positive = sum(marker in normalized for marker in POSITIVE_MARKERS)
    negative = sum(marker in normalized for marker in NEGATIVE_MARKERS)
    if positive > negative:
        return min(15.0, 8.0 + 3.5 * positive), "positive"
    if negative > positive:
        return 0.0, "negative"
    return 4.0, "neutral"


def _reaction_score(value: Any) -> float:
    try:
        change = float(value)
    except (TypeError, ValueError):
        return 0.0
    if change <= 0:
        return 0.0
    if change >= 10:
        return 10.0
    if change >= 5:
        return 7.0
    if change >= 2:
        return 4.0
    return 2.0


def _volume_score(value: Any) -> float:
    try:
        rvol = float(value)
    except (TypeError, ValueError):
        return 0.0
    if rvol >= 3:
        return 10.0
    if rvol >= 2:
        return 8.0
    if rvol >= 1.5:
        return 6.0
    if rvol >= 1:
        return 3.0
    return 0.0


def _classification(score: float) -> str:
    if score >= 90:
        return "EXTREME_EVENT"
    if score >= 75:
        return "STRONG_CATALYST"
    if score >= 60:
        return "MATERIAL_CATALYST"
    if score >= 40:
        return "SECONDARY"
    return "NOISE"


def evaluate_premarket_catalysts(
    symbol: str,
    news_items: list[dict[str, Any]] | None = None,
    earnings_items: list[dict[str, Any]] | None = None,
    market_context: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    context = market_context or {}
    items = [item for item in (news_items or []) if isinstance(item, dict)]
    for item in earnings_items or []:
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("title", "Earnings calendar event")
            normalized.setdefault("event_type", "earnings")
            items.append(normalized)

    unique_sources = {_source_identity(item) for item in items if _source_identity(item) != "unknown"}
    evaluated: list[dict[str, Any]] = []
    for item in items:
        title = _headline(item)
        event_type, materiality = _category(f"{item.get('event_type', '')} {title}")
        published_raw = _first(item, ("published", "published_at", "timestamp", "datetime", "date", "time"))
        published = parse_timestamp(published_raw)
        freshness, age_hours = _freshness_score(published_raw, current)
        surprise, direction = _surprise_and_direction(title)
        sympathy = 5.0 if event_type == "sympathy_sector" else 0.0
        evaluated.append(
            {
                "headline": title,
                "event_type": event_type,
                "source": _source_identity(item),
                "authoritative": _is_authoritative(item),
                "recognized": _is_recognized(item),
                "published_at": published.isoformat() if published else None,
                "age_hours": round(age_hours, 3) if age_hours is not None else None,
                "materiality": materiality,
                "freshness": freshness,
                "surprise": surprise,
                "direction": direction,
                "sympathy_sector": sympathy,
            }
        )

    best = max(evaluated, key=lambda event: (event["materiality"] + event["freshness"] + event["surprise"]), default=None)
    related_events = [event for event in evaluated if best and event["event_type"] == best["event_type"]]
    authoritative = [event for event in related_events if event["authoritative"]]
    recognized_sources = {event["source"] for event in related_events if event["recognized"] and event["source"] != "unknown"}
    if authoritative:
        validation_state = "confirmed_authoritative"
        source_score = 15.0
        confirmed = True
        validation_reason = "authoritative_source_present_for_primary_event"
    elif len(recognized_sources) >= 2:
        validation_state = "confirmed_corroborated"
        source_score = 12.0
        confirmed = True
        validation_reason = "two_independent_recognized_sources_for_primary_event"
    elif len(recognized_sources) == 1:
        validation_state = "supported_not_confirmed"
        source_score = 8.0
        confirmed = False
        validation_reason = "single_recognized_source_for_primary_event"
    else:
        validation_state = "unverified"
        source_score = 0.0
        confirmed = False
        validation_reason = "no_authoritative_or_corroborated_source_for_primary_event"

    reaction = _reaction_score(context.get("premarket_change", context.get("premarket_gap")))
    volume = _volume_score(context.get("premarket_rvol", context.get("rvol_10d")))
    breakdown = {
        "materiality": best["materiality"] if best else 0.0,
        "freshness": best["freshness"] if best else 0.0,
        "source_confirmation": source_score,
        "surprise": best["surprise"] if best else 0.0,
        "premarket_reaction": reaction,
        "premarket_volume": volume,
        "sympathy_sector": best["sympathy_sector"] if best else 0.0,
    }
    raw_score = round(min(100.0, sum(breakdown.values())), 2)
    recent = bool(best and best["freshness"] > 0)
    confirmed_recent = confirmed and recent
    direction = best["direction"] if best else "neutral"
    if confirmed_recent and direction == "positive":
        ranking_credit = raw_score
    elif confirmed_recent and direction == "neutral":
        ranking_credit = round(raw_score * 0.5, 2)
    else:
        ranking_credit = 0.0
    reasons = [validation_reason]
    if best is None:
        reasons.append("no_catalyst_items")
    elif best["age_hours"] is None:
        reasons.append("publication_timestamp_missing")
    elif best["freshness"] == 0:
        reasons.append("catalyst_stale")
    if not confirmed:
        reasons.append("unvalidated_catalyst_gets_no_confirmed_ranking_credit")
    elif not recent:
        reasons.append("stale_or_undated_catalyst_gets_no_recent_catalyst_credit")
    elif direction == "negative":
        reasons.append("negative_catalyst_gets_no_long_ranking_credit")

    return {
        "ticker": str(symbol).upper().split(":")[-1],
        "catalyst_score": raw_score,
        "catalyst_ranking_credit": ranking_credit,
        "catalyst_classification": _classification(raw_score),
        "catalyst_score_breakdown": breakdown,
        "confirmed_catalyst": confirmed_recent,
        "validation_state": validation_state,
        "validation_reasons": reasons,
        "primary_event_type": best["event_type"] if best else None,
        "direction": direction,
        "source_count": len(unique_sources),
        "headlines": [event["headline"] for event in evaluated if event["headline"]][:3],
        "events": evaluated,
    }
