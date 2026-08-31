from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def universe_hash(symbols: list[str]) -> str:
    normalized = "\n".join(str(symbol).upper().strip() for symbol in symbols)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_scanner_audit(
    *,
    run_id: str,
    started_at: datetime,
    completed_at: datetime,
    universe_symbols: list[str],
    universe_source: str,
    candidates: list[dict[str, Any]],
    global_warnings: list[str] | None = None,
) -> dict[str, Any]:
    records = []
    for candidate in candidates:
        provenance = candidate.get("data_provenance") or {}
        quality_states = sorted(
            {
                str(record.get("quality_state"))
                for record in provenance.values()
                if isinstance(record, dict) and record.get("quality_state")
            }
        )
        records.append(
            {
                "ticker": candidate.get("ticker"),
                "score": candidate.get("total_score"),
                "catalyst_score": candidate.get("catalyst_score", 0),
                "catalyst_classification": candidate.get("catalyst_classification", "NOISE"),
                "confirmed_catalyst": bool(candidate.get("has_recent_catalyst")),
                "catalyst_validation_state": candidate.get("catalyst_validation_state", "unverified"),
                "quality_states": quality_states,
                "provenance": provenance,
                "missing_fields": candidate.get("missing_fields") or [],
                "warnings": candidate.get("warnings") or [],
                "ranking_reasons": candidate.get("reasons") or [],
            }
        )
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "completed_at": completed_at.astimezone(timezone.utc).isoformat(),
        "universe": {
            "name": "Nasdaq-100 declared scanner universe",
            "source": universe_source,
            "symbol_count": len(universe_symbols),
            "sha256": universe_hash(universe_symbols),
            "symbols": universe_symbols,
        },
        "candidate_count": len(records),
        "candidates": records,
        "global_warnings": global_warnings or [],
    }


def write_scanner_audit(audit: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
