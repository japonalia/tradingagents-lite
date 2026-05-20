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


Diagnóstico específico de `analyze_multi_timeframe_batch`:

```bash
PYTHONPATH=. python tools/test_tvremix_multitimeframe_batch.py
```

Genera `reports/generated/tvremix_multitimeframe_batch_test.json` con salida sanitizada y campos detectados por símbolo.

## Uso

Ejecuta el comando:

```bash
python -m src.cli ticker NVDA
```

Puedes indicar fuente explícita:

```bash
python -m src.cli ticker NVDA --source yfinance
python -m src.cli ticker NVDA --source tvremix
python -m src.cli scan-nasdaq100 --source tvremix --limit 10 --technical-top-n 25 --catalyst-top-n 10
```

Esto hace:
- Obtiene datos de mercado e histórico diario desde la capa de proveedores.
- Calcula indicadores técnicos básicos (SMA, RSI, MACD, ATR).
- Calcula niveles simples de soporte/resistencia y rangos recientes.
- Genera un informe Markdown optimizado para pegar directo en GPT TradingAgents (Plantilla 7 / Modo B), con resumen ejecutivo, estado de candidata intradía y limitaciones de datos.

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

Scanner Nasdaq 100 operativo: usa `config/nasdaq100_symbols.yaml` (universo amplio), consulta `get_quotes_batch` para todo el universo en **chunks de hasta 50 símbolos** (límite de TVRemix), hace scoring preliminar y limita consultas costosas por fases: técnicos para `--technical-top-n`, niveles OHLCV intradía para `--ohlcv-top-n` y catalizadores para `--catalyst-top-n`. El reporte incluye warnings globales separados de warnings por ticker.
- Fuerza relativa vs QQQ incluida en scanner: **RS vs QQQ = variación % de la acción − variación % de QQQ** (si QQQ no está disponible, se deja como N/A y se reporta warning global).
- Niveles intradía opcionales desde `get_ohlcv`: se calculan solo para el Top preliminar, no para todo el universo, e incluyen high/low intradía, rango %, cierre intradía, VWAP aproximado desde barras, distancia a VWAP, banderas cerca de high/low y soporte/resistencia aproximados.
- Recalibración intradía activa en scoring: ahora se penaliza explícitamente RVOL bajo, movimientos fuertes sin confirmación de volumen y extensiones excesivas sobre VWAP; además, se aplican topes de score cuando no hay catalizador confirmado y el RVOL es bajo.

- Salida optimizada para GPT TradingAgents / Plantilla 7: el reporte `reports/generated/nasdaq100_scan_report.md` agrega una lectura ejecutiva rápida (Top 1, setup quality, estado de candidata, riesgo principal) + interpretación de mercado + limitaciones de datos, sin alterar el scoring base.


Parámetros del scanner Nasdaq 100:
- `--limit`: limita solo cuántas filas se muestran en el ranking final del reporte.
- `--technical-top-n`: limita cuántas candidatas preliminares reciben consultas técnicas (`analyze_multi_timeframe_batch` y fallback individual).
- `--intraday-top-n`: limita cuántas candidatas preliminares reciben fallback intradía con `get_symbol_data` cuando `run_screener` no cubre bien el universo Nasdaq 100.
- `--catalyst-top-n`: limita cuántas candidatas preliminares reciben consultas de catalizadores.
- `--ohlcv-top-n`: limita cuántas candidatas preliminares reciben consulta `get_ohlcv` para calcular niveles intradía. Por defecto es `5`, para evitar solicitar barras de los 98 símbolos del universo.
- `--ohlcv-interval`: intervalo de barras usado en `get_ohlcv` para los niveles intradía. Por defecto es `5m`; puedes usar otro intervalo soportado por TVRemix.
- `--skip-news`: omite consulta de `get_news` para reducir ruido/costo cuando solo quieres técnicos.
- `--skip-earnings` / `--no-skip-earnings`: controla consulta de `get_earnings_calendar` (por defecto `--skip-earnings` activado para evitar ruido y rate limits).
- `--skip-intraday`: desactiva enriquecimiento intradía desde `run_screener` (RVOL/VWAP/premarket/gap).
- `--skip-ohlcv-levels`: omite la capa de niveles intradía desde `get_ohlcv`; el scanner sigue funcionando con quotes, técnicos, RVOL/VWAP de screener y fuerza relativa.
- `--max-symbols`: límite opcional del universo evaluado (solo debug/pruebas). Por defecto `None` para evaluar todo `config/nasdaq100_symbols.yaml`.
- `--external-catalysts`: capa opcional/experimental de catalizadores externos para el Top final. Actualmente usa un stub seguro y, si no hay proveedor configurado, no rompe el scanner.


Recomendación operativa del scanner:
- Primera pasada: usar scanner sin earnings (default) para maximizar estabilidad y legibilidad del reporte.
- Activar `--no-skip-earnings` solo cuando necesites confirmar eventos cercanos y aceptes mayor ruido/riesgo de rate limit.
- Modo estable recomendado (sin noticias): usar `--catalyst-top-n 0 --skip-news --skip-earnings`.
- Para activar catalizadores TVRemix en modo prudente, usar `--catalyst-top-n 5 --skip-earnings` (consulta noticias solo para Top final y evita barrer todo el universo).
- Para preparar capa externa (experimental, sin API real): añadir `--external-catalysts`; si no hay proveedor configurado, el reporte indicará "Fuente externa de catalizadores no configurada."

Diagnóstico de `get_news` (TVRemix):

```bash
python tools/test_tvremix_news_fields.py
```

Guarda salida sanitizada en `reports/generated/tvremix_news_fields_test.json` y muestra:
- top-level keys,
- tipo de payload y parseo,
- detección de `content.text` y si parece JSON,
- campos posibles de titulares (`title`, `headline`, `published`, `provider`, `source`, `url`, `summary`).

- Diagnóstico intradía experimental: `PYTHONPATH=. python tools/test_tvremix_intraday_fields.py`
- Los campos RVOL/VWAP/premarket del scanner se leen desde `run_screener` cuando TVRemix los devuelve para el símbolo.
- Si `run_screener` devuelve cobertura baja del universo (ej. <5 símbolos parseables), el scanner usa fallback práctico: consulta `get_symbol_data` **solo** para el Top preliminar (`--intraday-top-n`, default 10), evitando pedir intradía para todo el universo y reduciendo riesgo de rate limit.


Ejemplos de scanner con y sin niveles OHLCV intradía:

```bash
python -m src.cli scan-nasdaq100 --source tvremix --limit 10 --technical-top-n 10 --intraday-top-n 10 --ohlcv-top-n 5 --catalyst-top-n 0 --skip-news --skip-earnings
python -m src.cli scan-nasdaq100 --source tvremix --limit 10 --technical-top-n 10 --intraday-top-n 10 --catalyst-top-n 0 --skip-news --skip-earnings --skip-ohlcv-levels
python -m src.cli scan-nasdaq100 --source tvremix --limit 10 --technical-top-n 10 --intraday-top-n 10 --ohlcv-top-n 5 --catalyst-top-n 5 --skip-earnings --external-catalysts
```

Auditoría de universo Nasdaq 100:

```bash
python tools/audit_nasdaq100_universe.py
```
