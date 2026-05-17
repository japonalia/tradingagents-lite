# TradingAgents Lite

TradingAgents Lite es una herramienta mínima en Python para generar una ficha técnica/fundamental básica en Markdown para un ticker.

> Esta versión **no** usa APIs LLM, no ejecuta trading y no emite recomendaciones financieras automáticas.

## Estado actual de fuentes de datos

- La fuente activa y soportada hoy es **yfinance**.
- El proyecto ya incluye una **capa abstracta de proveedores de datos** para permitir múltiples fuentes en el futuro.
- **TVRemix MCP todavía no está integrado**; queda como siguiente paso.

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

Opcionalmente puedes indicar la fuente (por ahora solo `yfinance`):

```bash
python -m src.cli ticker NVDA --source yfinance
```

Esto hace:
- Obtiene datos de mercado e histórico diario desde `yfinance` mediante la capa de proveedores.
- Calcula indicadores técnicos básicos (SMA, RSI, MACD, ATR).
- Calcula niveles simples de soporte/resistencia y rangos recientes.
- Genera un informe Markdown bruto listo para pegar en TradingAgents GPT.

Si se solicita una fuente no soportada, el CLI informa claramente:

- `Fuente de datos no soportada todavía`

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
