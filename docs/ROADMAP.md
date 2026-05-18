# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual**: integración inicial intradía en scanner Nasdaq 100 vía `run_screener` (RVOL, VWAP, gap/premarket + modo `technical_intraday`).
7. 🔜 **Próximos pasos**: fuerza relativa vs QQQ, niveles intradía desde `get_ohlcv` y catalizadores reales.


## Estado intradía TVRemix (experimental)
- Paso actual: integración básica de RVOL/VWAP/premarket usando `run_screener`, con fallback a quotes+técnicos cuando falte intradía.
- Próximos pasos: fuerza relativa vs QQQ, niveles intradía derivados de barras `get_ohlcv`, y mejor capa de catalizadores verificables.
