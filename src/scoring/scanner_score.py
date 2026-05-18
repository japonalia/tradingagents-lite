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
    warnings = list(candidate.get("warnings") or [])
    penalties: list[str] = []

    # Momentum / change_percent: 0-15
    momentum = 0.0
    cp = _to_float(candidate.get("change_percent"))
    if cp is None:
        reasons.append("Sin change_percent.")
    else:
        momentum = max(0.0, min(15.0, 7.5 + cp * 1.2))

    # Volumen / liquidez: 0-15
    volume_score = 15.0 if candidate.get("volume") not in (None, "") else 0.0
    if not volume_score:
        reasons.append("Sin volumen.")

    # Intradía (RVOL/VWAP/Gap): 0-10
    intraday = 0.0
    rvol = _to_float(candidate.get("rvol_10d"))
    vwap = _to_float(candidate.get("vwap"))
    intraday_price = _to_float(candidate.get("intraday_close"))
    if intraday_price is None:
        intraday_price = _to_float(candidate.get("price"))
    gap = _to_float(candidate.get("gap"))
    premarket_gap = _to_float(candidate.get("premarket_gap"))
    intraday_change = _to_float(candidate.get("intraday_change"))

    if rvol is not None and rvol >= 1.5:
        intraday += 2.5
    if rvol is not None and rvol >= 2.0:
        intraday += 2.5
    if intraday_price is not None and vwap is not None and intraday_price > vwap:
        intraday += 2.0
    if (gap is not None and abs(gap) >= 1.0) or (premarket_gap is not None and abs(premarket_gap) >= 1.0):
        intraday += 1.5
    if (intraday_change is not None and abs(intraday_change) >= 3.0) and (rvol is None or rvol < 1.2):
        intraday -= 2.0
        penalties.append("Movimiento fuerte sin RVOL suficiente.")
    intraday = max(0.0, min(10.0, intraday))

    # Técnico / rating / RSI: 0-20
    technical = 0.0
    rating = str(candidate.get("technical_rating") or "").upper()
    rating_map = {
        "STRONG_BUY": 12,
        "BUY": 9,
        "NEUTRAL": 6,
        "SELL": 3,
        "STRONG_SELL": 0,
    }
    matched = next((v for k, v in rating_map.items() if k in rating), None)
    if matched is None:
        reasons.append("Sin rating técnico utilizable.")
    else:
        technical += float(matched)

    rsi = _to_float(candidate.get("rsi"))
    if rsi is None:
        reasons.append("Sin RSI.")
    elif 45 <= rsi <= 65:
        technical += 8
    elif 35 <= rsi < 45 or 65 < rsi <= 75:
        technical += 5
    else:
        technical += 3
    technical = min(20.0, technical)

    # Catalizador / noticias / earnings: 0-20
    catalyst = 0.0
    if candidate.get("news_count", 0) > 0:
        catalyst += min(12.0, 4.0 * float(candidate.get("news_count", 0)))
    if candidate.get("earnings_nearby"):
        catalyst += 8.0
    if not candidate.get("has_recent_catalyst"):
        catalyst = max(0.0, catalyst - 6.0)
        penalties.append("Sin catalizador confirmado.")
    catalyst = min(20.0, catalyst)

    # Data quality: 0-20
    data_quality = max(0.0, 20.0 - len(set(missing_fields)) * 4.0)

    # Riesgo / penalizaciones: 0-10
    risk = 10.0
    if "STRONG_SELL" in rating:
        risk -= 4
        penalties.append("Rating técnico Strong Sell.")
    if rsi is not None and rsi > 75:
        risk -= 2
        warnings.append("RSI > 75: posible sobreextensión.")
    if cp is not None and cp >= 4 and not candidate.get("has_recent_catalyst"):
        risk -= 2
        warnings.append("FOMO: subida fuerte sin noticia confirmada.")
    if cp is not None and cp <= -4 and not candidate.get("has_recent_catalyst"):
        risk -= 2
        warnings.append("Caída fuerte sin noticia confirmada.")
    risk = max(0.0, risk)

    total = momentum + volume_score + intraday + technical + catalyst + data_quality + risk

    return {
        "total_score": round(min(100.0, total), 2),
        "score_breakdown": {
            "momentum": round(momentum, 2),
            "volume_liquidity": round(volume_score, 2),
            "intraday": round(intraday, 2),
            "technical": round(technical, 2),
            "catalyst": round(catalyst, 2),
            "data_quality": round(data_quality, 2),
            "risk": round(risk, 2),
        },
        "reasons": reasons + penalties,
        "warnings": warnings,
        "missing_fields": missing_fields,
    }
