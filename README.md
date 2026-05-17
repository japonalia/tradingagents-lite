# TradingAgents Lite

TradingAgents Lite es una herramienta mínima en Python para generar una ficha técnica/fundamental básica en Markdown para un ticker.

> Esta versión **no** usa APIs LLM, no ejecuta trading y no emite recomendaciones financieras automáticas.

## Estado actual de fuentes de datos

- Fuente soportada principal: **yfinance**.
- Soporte inicial opcional para **TVRemix MCP** (mapeo real inicial para `get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`).
- Si TVRemix falla en runtime, el proveedor aplica fallback a **yfinance** con aviso legible.

## Instalación

1. Crear y activar entorno virtual (opcional, recomendado).
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Configurar TVRemix MCP

Añade estas variables a tu `.env` local:

```env
TVREMIX_MCP_URL=https://tvremix.xyz/api/mcp/v1
TVREMIX_API_KEY=tu_clave_aqui
```

Notas:
- No incluyas claves reales en commits.
- Si ejecutas `--source tvremix` sin configuración válida, verás:
  - `TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.`


## Diagnóstico TVRemix MCP

Para inspeccionar el schema real de herramientas MCP localmente (sin exponer secretos), ejecuta:

```bash
python tools/diagnose_tvremix.py
```

Este script:
- Carga variables desde `.env` usando `python-dotenv`.
- Requiere `TVREMIX_MCP_URL` y `TVREMIX_API_KEY` (si faltan, termina con error claro).
- Llama a TVRemix vía JSON-RPC 2.0 con `method: tools/list` y headers `Accept: application/json, text/event-stream`.
- Muestra `status_code`, nombres de tools, descripción e `inputSchema` cuando exista.
- Guarda una copia sanitizada en `reports/generated/tvremix_tools_schema.json` sin API key ni headers sensibles.

Buenas prácticas:
- No imprimas ni compartas tu `TVREMIX_API_KEY`.
- No subas `.env` al repositorio.


## Test de símbolo TVRemix

Para validar el primer mapeo real del ticker NVDA:

```bash
python tools/test_tvremix_symbol.py
```

El script prueba `get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv` y guarda salida sanitizada en:

```text
reports/generated/tvremix_NVDA_test.json
```

## Uso

Ejecuta el comando:

```bash
python -m src.cli ticker NVDA
```

Puedes indicar fuente explícita:

```bash
python -m src.cli ticker NVDA --source yfinance
python -m src.cli ticker NVDA --source tvremix
python -m src.cli scan-nasdaq100 --source tvremix --limit 10
```

Esto hace:
- Obtiene datos de mercado e histórico diario desde la capa de proveedores.
- Calcula indicadores técnicos básicos (SMA, RSI, MACD, ATR).
- Calcula niveles simples de soporte/resistencia y rangos recientes.
- Genera un informe Markdown bruto listo para pegar en TradingAgents GPT.

Comportamiento con TVRemix:
- Si pasas `NVDA`, se normaliza a `NASDAQ:NVDA` internamente para TVRemix.
- Para otros mercados usa formato TradingView (ej. `NYSE:IBM`).
- Si hay diferencias de schema, no se inventan campos: se reportan warnings y claves observadas.
- Si TVRemix falla completamente, el sistema usa fallback yfinance y deja aviso explícito.

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

## Estado del scanner Nasdaq 100

Scanner inicial implementado: usa `config/nasdaq100_symbols.yaml`, consulta `get_quotes_batch` + `get_technicals` y genera `reports/generated/nasdaq100_scan_report.md`.
