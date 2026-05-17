# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual**: scanner Nasdaq 100 con noticias/catalizadores básicos (`get_news` por símbolo y `get_earnings_calendar` cuando disponible), scoring reequilibrado y reporte con sección de catalizadores.
7. 🔜 **Próximos pasos**: RVOL, premarket high/low, VWAP, scoring avanzado multicapa y salida de reporte lista para GPT.
