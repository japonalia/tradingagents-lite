# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Fuerza relativa vs QQQ en scanner Nasdaq 100**: `RS vs QQQ = cambio de la acción - cambio de QQQ` con warning global si QQQ no está disponible.
7. ✅ **Paso actual**: niveles intradía desde `get_ohlcv` para Top candidatas preliminares, sin consultar barras para todo el universo.
8. 🔜 **Próximos pasos**: catalizadores reales/noticias verificables y validación final para GPT.


## Estado intradía TVRemix (experimental)
- Paso actual: niveles intradía derivados de barras `get_ohlcv` para un Top N pequeño (`--ohlcv-top-n`, default 5), con high/low, rango %, último cierre intradía, VWAP aproximado desde barras, distancia a VWAP, cercanía a high/low, soporte y resistencia aproximados.
- Mantener: fuerza relativa vs QQQ integrada al ranking y reporte, manteniendo `technical_intraday` cuando hay capa intradía.
- Próximos pasos: integrar catalizadores reales/noticias verificables y preparar una validación final para uso seguro en GPT.
