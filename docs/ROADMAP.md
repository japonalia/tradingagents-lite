# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual**: mapeo real defensivo de `analyze_multi_timeframe_batch` para extraer rating técnico/RSI/MACD/medias por símbolo, manteniendo fallback individual acotado y anti-rate-limit en scanner Nasdaq 100.
7. 🔜 **Próximos pasos**: `get_news` enriquecido, RVOL, VWAP, premarket high/low y fuerza relativa vs QQQ.
