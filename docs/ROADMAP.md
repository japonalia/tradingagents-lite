# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual/completado**: fuerza relativa vs QQQ en scanner Nasdaq 100 (`RS vs QQQ = cambio de la acción - cambio de QQQ`) con warning global si QQQ no está disponible.
7. 🔜 **Próximos pasos**: niveles intradía desde `get_ohlcv` y catalizadores reales.


## Estado intradía TVRemix (experimental)
- Paso actual/completado: fuerza relativa vs QQQ integrada al ranking y reporte, manteniendo `technical_intraday` cuando hay capa intradía.
- Próximos pasos: niveles intradía derivados de barras `get_ohlcv` y mejor capa de catalizadores verificables.
