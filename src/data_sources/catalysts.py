from __future__ import annotations


def _external_catalysts_configured() -> bool:
    """Placeholder para futura integración de proveedor externo real."""
    return False


def fetch_external_catalysts(symbols: list[str], limit_per_symbol: int = 3) -> dict:
    _ = max(1, int(limit_per_symbol))
    configured = _external_catalysts_configured()
    result: dict[str, dict] = {}

    for symbol in symbols:
        key = str(symbol).upper().strip()
        if not key:
            continue
        if not configured:
            result[key] = {
                "has_recent_catalyst": False,
                "catalyst_summary": "Sin catalizador externo configurado",
                "catalyst_headlines": [],
                "catalyst_source_count": 0,
                "warnings": ["fuente externa de catalizadores no configurada"],
            }
            continue

        result[key] = {
            "has_recent_catalyst": False,
            "catalyst_summary": "Sin catalizador externo configurado",
            "catalyst_headlines": [],
            "catalyst_source_count": 0,
            "warnings": [],
        }

    return result
