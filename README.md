# TradingAgents Lite

TradingAgents Lite es una herramienta mínima en Python para generar una ficha técnica/fundamental básica en Markdown para un ticker.

> Esta versión **no** usa APIs LLM, no ejecuta trading y no emite recomendaciones financieras automáticas.

## Instalación

1. Crear y activar entorno virtual (opcional, recomendado).
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Uso

Ejecuta el comando:

```bash
python -m src.cli ticker NVDA
```

Esto hace:
- Descarga datos de mercado e histórico diario desde `yfinance` (fuente inicial/fallback).
- Calcula indicadores técnicos básicos (SMA, RSI, MACD, ATR).
- Calcula niveles simples de soporte/resistencia y rangos recientes.
- Genera un informe Markdown bruto listo para pegar en TradingAgents GPT.

## Salida

El informe se guarda en:

```text
reports/generated/[TICKER]_report.md
```

Por ejemplo:

```text
reports/generated/NVDA_report.md
```

## Prueba sin internet

Si no puedes usar `yfinance` o no tienes internet, puedes generar un informe de ejemplo local usando datos ficticios incluidos en el repositorio.

1. Instala dependencias locales (solo `pandas` y las ya listadas en `requirements.txt`).
2. Ejecuta:

```bash
python tools/generate_sample_report.py
```

El script:
- Lee `data/sample/NVDA_sample_daily.csv`.
- Calcula indicadores técnicos y niveles con los módulos actuales.
- Genera `reports/generated/NVDA_sample_report.md`.

Esta ruta permite validar el MVP end-to-end sin depender de APIs externas ni conexión de red.
