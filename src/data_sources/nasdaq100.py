from __future__ import annotations

from pathlib import Path


def _parse_simple_yaml_symbols(text: str) -> list[str]:
    symbols: list[str] = []
    in_symbols = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "symbols:" or line.startswith("symbols:"):
            in_symbols = True
            continue
        if in_symbols and line.startswith("-"):
            value = line[1:].strip().strip('"').strip("'")
            if value:
                symbols.append(value.upper())
    return symbols


def load_nasdaq100_symbols(path: str = "config/nasdaq100_symbols.yaml") -> list[str]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"No existe archivo de símbolos Nasdaq 100: {file_path}")

    symbols = _parse_simple_yaml_symbols(file_path.read_text(encoding="utf-8"))
    if not symbols:
        raise ValueError("No se pudieron leer símbolos desde YAML (formato esperado: clave 'symbols' con lista).")
    return symbols
