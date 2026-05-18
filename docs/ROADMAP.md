# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual**: fallback intradía por Top preliminar en scanner Nasdaq 100: primer intento con `run_screener` y, si la cobertura del universo es baja, `get_symbol_data` para `--intraday-top-n` (no para todo el universo).
7. 🔜 **Próximos pasos**: fuerza relativa vs QQQ, niveles intradía desde `get_ohlcv` y catalizadores reales.


## Estado intradía TVRemix (experimental)
- Paso actual: `run_screener` como fuente intradía primaria + fallback `get_symbol_data` para Top preliminar cuando no hay cobertura útil del universo.
- Próximos pasos: fuerza relativa vs QQQ, niveles intradía derivados de barras `get_ohlcv`, y mejor capa de catalizadores verificables.
