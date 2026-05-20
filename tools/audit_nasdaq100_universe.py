from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.data_sources.nasdaq100 import load_nasdaq100_symbols

OUTPUT_PATH = Path("reports/generated/nasdaq100_universe_audit.md")
KNOWN_PROBLEMATIC_SYMBOLS = {
    "NASDAQ:GOOG": "Dual-class con GOOGL (verificar si ambos deben coexistir según criterio interno).",
    "NASDAQ:GOOGL": "Dual-class con GOOG (verificar si ambos deben coexistir según criterio interno).",
}
SYMBOL_PATTERN = re.compile(r"^[A-Z]+:[A-Z0-9.\-]+$")


def split_symbol(symbol: str) -> tuple[str | None, str]:
    if ":" not in symbol:
        return None, symbol
    prefix, ticker = symbol.split(":", 1)
    return prefix, ticker


def main() -> int:
    symbols = load_nasdaq100_symbols()
    symbols_sorted = sorted(symbols)

    counter = Counter(symbols)
    duplicates = sorted([sym for sym, count in counter.items() if count > 1])

    without_nasdaq_prefix = sorted([sym for sym in symbols if not sym.startswith("NASDAQ:")])

    weird_format = sorted([sym for sym in symbols if SYMBOL_PATTERN.fullmatch(sym) is None])

    non_uppercase = sorted([sym for sym in symbols if sym != sym.upper()])

    problematic = sorted([sym for sym in symbols if sym in KNOWN_PROBLEMATIC_SYMBOLS])

    lines: list[str] = []
    lines.append("# Auditoría de universo Nasdaq 100 (scanner)")
    lines.append("")
    lines.append("## Resumen")
    lines.append(f"- Total de símbolos cargados: **{len(symbols)}**")
    lines.append("- Nota: el universo actual contiene **98 símbolos** (no 100).")
    lines.append("- Referencia externa: **no aplicada** en esta auditoría (pendiente comparación manual futura).")
    lines.append("")

    lines.append("## Chequeos de calidad")
    lines.append(f"- Duplicados detectados: **{len(duplicates)}**")
    if duplicates:
        for sym in duplicates:
            lines.append(f"  - {sym} (repetido {counter[sym]} veces)")
    else:
        lines.append("  - Ninguno")

    lines.append(f"- Símbolos sin prefijo `NASDAQ:`: **{len(without_nasdaq_prefix)}**")
    if without_nasdaq_prefix:
        for sym in without_nasdaq_prefix:
            lines.append(f"  - {sym}")
    else:
        lines.append("  - Ninguno")

    lines.append(f"- Símbolos con formato raro: **{len(weird_format)}**")
    if weird_format:
        for sym in weird_format:
            lines.append(f"  - {sym}")
    else:
        lines.append("  - Ninguno")

    lines.append(f"- Símbolos no normalizados a mayúsculas: **{len(non_uppercase)}**")
    if non_uppercase:
        for sym in non_uppercase:
            lines.append(f"  - {sym}")
    else:
        lines.append("  - Ninguno")

    lines.append(f"- Símbolos conocidos potencialmente problemáticos: **{len(problematic)}**")
    if problematic:
        for sym in problematic:
            lines.append(f"  - {sym}: {KNOWN_PROBLEMATIC_SYMBOLS[sym]}")
    else:
        lines.append("  - Ninguno")
    lines.append("")

    lines.append("## Lista completa ordenada")
    for sym in symbols_sorted:
        prefix, ticker = split_symbol(sym)
        if prefix is None:
            lines.append(f"- {sym}")
        else:
            lines.append(f"- {prefix}:{ticker}")

    lines.append("")
    lines.append("## Nota para siguiente fase")
    lines.append(
        "Esta auditoría no cambia el universo ni valida contra una lista externa. "
        "Se deja este archivo como base para una comparación manual futura."
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Total symbols: {len(symbols)}")
    print("Universe currently contains 98 symbols.")
    print(f"Duplicates: {len(duplicates)}")
    print(f"Without NASDAQ prefix: {len(without_nasdaq_prefix)}")
    print(f"Weird format: {len(weird_format)}")
    print(f"Known potentially problematic: {len(problematic)}")
    print(f"Audit written to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
