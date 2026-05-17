# TradingAgents Lite

TradingAgents Lite es una herramienta mínima en Python para generar una ficha técnica/fundamental básica en Markdown para un ticker.

> Esta versión **no** usa APIs LLM, no ejecuta trading y no emite recomendaciones financieras automáticas.

## Estado actual de fuentes de datos

- Fuente soportada principal: **yfinance**.
- Soporte inicial opcional para **TVRemix MCP** (integración defensiva; schema aún pendiente de mapear).
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

## Uso

Ejecuta el comando:

```bash
python -m src.cli ticker NVDA
```

Puedes indicar fuente explícita:

```bash
python -m src.cli ticker NVDA --source yfinance
python -m src.cli ticker NVDA --source tvremix
```

Esto hace:
- Obtiene datos de mercado e histórico diario desde la capa de proveedores.
- Calcula indicadores técnicos básicos (SMA, RSI, MACD, ATR).
- Calcula niveles simples de soporte/resistencia y rangos recientes.
- Genera un informe Markdown bruto listo para pegar en TradingAgents GPT.

Comportamiento con TVRemix:
- Si TVRemix responde pero su schema aún no está mapeado, se avisa:
  - `TVRemix conectado parcialmente / schema pendiente de mapear`
- Si TVRemix falla, el sistema sigue con yfinance y muestra aviso de fallback.

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
