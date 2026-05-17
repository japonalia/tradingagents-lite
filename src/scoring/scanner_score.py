from __future__ import annotations


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def score_candidate(candidate: dict) -> dict:
    if not isinstance(candidate, dict):
        candidate = {}

    reasons: list[str] = []
    missing_fields = list(candidate.get("missing_fields") or [])
    score = 0.0

    cp = _to_float(candidate.get("change_percent"))
    if cp is None:
        reasons.append("Sin change_percent.")
    else:
        score += max(0.0, min(20.0, 10.0 + cp * 2.0))

    if candidate.get("volume") not in (None, ""):
        score += 15.0
    else:
        reasons.append("Sin volumen.")

    rating = str(candidate.get("technical_rating") or "").upper()
    rating_map = {
        "STRONG_BUY": 20,
        "BUY": 16,
        "NEUTRAL": 10,
        "SELL": 4,
        "STRONG_SELL": 0,
    }
    matched = next((v for k, v in rating_map.items() if k in rating), None)
    if matched is None:
        reasons.append("Sin rating técnico utilizable.")
    else:
        score += float(matched)

    rsi = _to_float(candidate.get("rsi"))
    if rsi is None:
        reasons.append("Sin RSI.")
    elif 45 <= rsi <= 65:
        score += 15
    elif 35 <= rsi < 45 or 65 < rsi <= 75:
        score += 10
    else:
        score += 5

    if candidate.get("market_cap") not in (None, ""):
        score += 10
    else:
        reasons.append("Sin market_cap.")

    quality = max(0, 20 - len(set(missing_fields)) * 4)
    score += quality

    return {
        "total_score": round(score, 2),
        "reasons": reasons,
        "missing_fields": missing_fields,
    }
