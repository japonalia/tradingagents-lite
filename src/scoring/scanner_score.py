from __future__ import annotations


REQUIRED_FIELDS = ["ticker", "last_price", "change_percent", "volume"]


def score_candidate(candidate: dict) -> dict:
    """Placeholder de scoring para el scanner Nasdaq 100.

    Esta versión no usa APIs externas ni fuentes remotas. Solo valida campos
    mínimos y devuelve una estructura estable para futuras fases.
    """
    if not isinstance(candidate, dict):
        candidate = {}

    missing_fields = [field for field in REQUIRED_FIELDS if candidate.get(field) in (None, "")]

    reasons: list[str] = []
    if missing_fields:
        reasons.append("Datos incompletos para scoring detallado.")

    total_score = 0
    if not missing_fields:
        reasons.append("Candidata válida para evaluación en la siguiente fase.")
        total_score = 50

    return {
        "ticker": candidate.get("ticker"),
        "total_score": total_score,
        "reasons": reasons,
        "missing_fields": missing_fields,
    }
