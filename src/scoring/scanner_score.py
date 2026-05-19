from __future__ import annotations


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_unique(messages: list[str], message: str) -> None:
    normalized = message.strip().lower()
    if not normalized:
        return
    if normalized not in {m.strip().lower() for m in messages}:
        messages.append(message)


def score_candidate(candidate: dict) -> dict:
    if not isinstance(candidate, dict):
        candidate = {}

    reasons: list[str] = []
    missing_fields = list(candidate.get("missing_fields") or [])
    warnings: list[str] = []
    for warning in (candidate.get("warnings") or []):
        _append_unique(warnings, str(warning).strip())
    penalties: list[str] = []
    intraday_expected = bool(candidate.get("intraday_expected") or candidate.get("use_intraday"))

    cp = _to_float(candidate.get("change_percent"))
    rvol = _to_float(candidate.get("rvol_10d"))

    # Momentum / change_percent: 0-15
    momentum = 0.0
    if cp is None:
        reasons.append("Sin change_percent.")
    else:
        momentum = max(0.0, min(15.0, 7.5 + cp * 1.2))

    rs_vs_qqq = _to_float(candidate.get("relative_strength_vs_qqq"))
    if rs_vs_qqq is not None:
        if rs_vs_qqq > 2.0:
            rs_bonus = 4.0
            if rvol is not None and rvol < 0.75:
                rs_bonus = 2.0
            momentum += rs_bonus
        elif rs_vs_qqq > 1.0:
            momentum += 2.0
        elif rs_vs_qqq < -1.0:
            momentum -= 2.0
            penalties.append("Bajo desempeño relativo vs QQQ.")
    momentum = max(0.0, min(15.0, momentum))

    # Volumen / liquidez: 0-15
    volume_score = 15.0 if candidate.get("volume") not in (None, "") else 0.0
    if not volume_score:
        reasons.append("Sin volumen.")

    # Intradía (RVOL/VWAP/Gap): 0-10
    intraday = 0.0
    vwap = _to_float(candidate.get("vwap"))
    intraday_price = _to_float(candidate.get("intraday_close"))
    if intraday_price is None:
        intraday_price = _to_float(candidate.get("price"))
    last_close_intraday = _to_float(candidate.get("last_close_intraday"))
    bars_vwap = _to_float(candidate.get("approx_intraday_vwap_from_bars"))
    gap = _to_float(candidate.get("gap"))
    premarket_gap = _to_float(candidate.get("premarket_gap"))
    distance_to_vwap_pct = _to_float(candidate.get("distance_to_vwap_pct"))

    if rvol is not None:
        if rvol >= 2.0:
            intraday += 8.0
        elif rvol >= 1.5:
            intraday += 5.0
        elif rvol >= 1.0:
            intraday += 2.0
        elif rvol < 0.25:
            intraday -= 10.0
            penalties.append("RVOL extremadamente bajo.")
        elif rvol < 0.5:
            intraday -= 7.0
            penalties.append("RVOL muy bajo.")
        elif rvol < 0.75:
            intraday -= 4.0
            penalties.append("RVOL bajo.")

    if intraday_price is not None and vwap is not None and intraday_price > vwap:
        intraday += 2.0
    if (gap is not None and abs(gap) >= 1.0) or (premarket_gap is not None and abs(premarket_gap) >= 1.0):
        intraday += 1.5
    if candidate.get("near_intraday_high") is True:
        if rvol is not None and rvol >= 1.0:
            intraday += 3.0
        else:
            _append_unique(warnings, "Cerca de máximo intradía pero sin RVOL suficiente.")
    if candidate.get("near_intraday_low") is True:
        intraday -= 1.5
        penalties.append("Cerca del mínimo intradía.")
    if last_close_intraday is not None and bars_vwap is not None:
        if last_close_intraday > bars_vwap:
            intraday += 1.0
        elif last_close_intraday < bars_vwap:
            intraday -= 1.0
            penalties.append("Último cierre intradía bajo VWAP de barras.")

    if cp is not None and rvol is not None:
        if abs(cp) >= 3.0 and rvol < 0.75:
            intraday -= 6.0
            _append_unique(warnings, "Movimiento fuerte sin confirmación de volumen.")
        elif abs(cp) >= 2.0 and rvol < 1.0:
            intraday -= 4.0
            _append_unique(warnings, "Movimiento fuerte con RVOL bajo.")

    if distance_to_vwap_pct is not None and distance_to_vwap_pct > 5:
        _append_unique(warnings, "Extendida sobre VWAP intradía.")
        if rvol is not None and rvol < 1.5:
            intraday -= 2.0
    if distance_to_vwap_pct is not None and distance_to_vwap_pct > 8:
        intraday -= 4.0
        _append_unique(warnings, "Riesgo de persecución: muy extendida sobre VWAP.")

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
    has_recent_catalyst = bool(candidate.get("has_recent_catalyst"))
    if not has_recent_catalyst:
        catalyst = max(0.0, catalyst - 6.0)
        penalties.append("Sin catalizador confirmado.")
    catalyst = min(20.0, catalyst)

    if intraday_expected:
        has_rvol = rvol is not None
        has_vwap = vwap is not None
        if not has_rvol and not has_vwap:
            _append_unique(warnings, "Sin RVOL/VWAP intradía.")
            penalties.append("Penalización por falta de RVOL/VWAP intradía.")
            total_intraday_penalty = -6.0
            intraday = max(0.0, intraday + total_intraday_penalty)
        elif not has_rvol and has_vwap:
            _append_unique(warnings, "RVOL no disponible.")
            penalties.append("Penalización por RVOL faltante.")
            intraday = max(0.0, intraday - 3.0)
        elif has_rvol and not has_vwap:
            _append_unique(warnings, "VWAP no disponible.")
            penalties.append("Penalización por VWAP faltante.")
            intraday = max(0.0, intraday - 2.0)

    # Data quality: 0-20
    data_quality = max(0.0, 20.0 - len(set(missing_fields)) * 4.0)

    # Riesgo / penalizaciones: 0-10
    risk = 10.0
    if "STRONG_SELL" in rating:
        risk -= 4
        penalties.append("Rating técnico Strong Sell.")
    if rsi is not None and rsi > 75:
        risk -= 2
        _append_unique(warnings, "RSI > 75: posible sobreextensión.")
    if cp is not None and cp >= 4 and not has_recent_catalyst:
        risk -= 2
        _append_unique(warnings, "FOMO: subida fuerte sin noticia confirmada.")
    if cp is not None and cp <= -4 and not has_recent_catalyst:
        risk -= 2
        _append_unique(warnings, "Caída fuerte sin noticia confirmada.")
    risk = max(0.0, risk)

    total = momentum + volume_score + intraday + technical + catalyst + data_quality + risk
    total = min(100.0, total)

    if rvol is not None and not has_recent_catalyst:
        if rvol < 0.25:
            total = min(total, 62.0)
        elif rvol < 0.5:
            total = min(total, 68.0)
        elif rvol < 0.75:
            total = min(total, 72.0)
    if intraday_expected and rvol is None and vwap is None and not has_recent_catalyst:
        total = min(total, 70.0)

    return {
        "total_score": round(total, 2),
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
